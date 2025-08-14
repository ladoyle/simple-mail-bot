from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import Depends
from sqlalchemy.orm import Session

from backend import database
from backend.database import EmailRule, EmailStatistic
from backend.gmail_client import GmailClient, get_gmail_client

_history_engine_singleton = None


def get_history_engine_service(
        db: Session = Depends(database.get_db),
        gmail_client: GmailClient = Depends(get_gmail_client),
):
    """
    Dependency to get a singleton MailHistoryEngineService.
    Call start() once on application boot to launch the scheduler.
    """
    global _history_engine_singleton
    if _history_engine_singleton is None:
        _history_engine_singleton = MailHistoryEngineService(db_session=db, gmail_client=gmail_client)
    return _history_engine_singleton


class MailHistoryEngineService:
    """
    History Engine:
    - At 4:00 AM (UTC) every day, aggregates Gmail history changes since the last run.
    - Builds a mapping from EmailRule.addLabelIds/removeLabelIds to EmailRule (id, name).
    - Uses Gmail history API to count labelAdded/labelRemoved occurrences per rule.
    - Persists a row in EmailStatistic with (timestamp, processed, rule_id, rule_name).

    Notes:
    - The Gmail History API requires a startHistoryId. We persist it in a small state file.
    - On first run (no stored history id), we initialize from the current profile historyId
      and skip backfill (to avoid processing all historical data).
    """

    STATE_FILE = ".gmail_history_state.json"  # stored under project base dir
    STATE_KEY = "last_history_id"

    def __init__(self, db_session: Session, gmail_client: GmailClient):
        self.db: Session = db_session
        self.gmail_client = gmail_client
        self._task: Optional[asyncio.Task] = None
        # Resolve state file under project root
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._state_path = os.path.join(base_dir, self.STATE_FILE)

    # ---------------------------
    # Public lifecycle
    # ---------------------------

    def start(self) -> None:
        """
        Starts the background scheduler (idempotent).
        """
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._scheduler_loop(), name="mail-history-engine-4am")

    def stop(self) -> None:
        """
        Cancels the background scheduler, if running.
        """
        if self._task and not self._task.done():
            self._task.cancel()

    # ---------------------------
    # Scheduler loop
    # ---------------------------

    async def _scheduler_loop(self) -> None:
        """
        Sleeps until the next 4:00 AM UTC, then runs aggregation daily.
        """
        try:
            while True:
                sleep_seconds = self._seconds_until_next_4am_utc()
                await asyncio.sleep(sleep_seconds)
                await self.run_once()
        except asyncio.CancelledError:
            # graceful stop
            return

    @staticmethod
    def _seconds_until_next_4am_utc() -> float:
        now = datetime.now(timezone.utc)
        next_run = now.replace(hour=4, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run = next_run + timedelta(days=1)
        return (next_run - now).total_seconds()

    # ---------------------------
    # Core execution
    # ---------------------------

    async def run_once(self) -> None:
        """
        Performs a single aggregation cycle:
        - Load rules and build label->rules mapping.
        - Fetch Gmail history since last_history_id.
        - Count label add/remove events per rule.
        - Insert EmailStatistic totals with current timestamp.
        - Update last_history_id.
        """
        # Build rule mappings
        rules = self.db.query(EmailRule).all()
        if not rules:
            self._ensure_last_history_initialized()
            return

        add_map, remove_map = self._build_label_rule_maps(rules)

        # Load startHistoryId (initialize from profile if missing)
        start_id = self._ensure_last_history_initialized()
        if start_id is None:
            # No history processed this time (just initialized to current), do nothing
            return

        # Pull history and count label events
        counts_by_rule: Dict[int, int] = {r.id: 0 for r in rules}
        newest_history_id = start_id

        for history, newest_history_id in self._iter_history_since(start_id):
            # history is a dict with possible 'labelsAdded'/'labelsRemoved'
            for added in history.get("labelsAdded", []):
                label_ids = set(added.get("labelIds", []) or [])
                self._accumulate(counts_by_rule, add_map, label_ids)

            for removed in history.get("labelsRemoved", []):
                label_ids = set(removed.get("labelIds", []) or [])
                self._accumulate(counts_by_rule, remove_map, label_ids)

        # Persist totals with current timestamp
        ts = int(datetime.now(timezone.utc).timestamp())
        stats_to_add: List[EmailStatistic] = []
        for r in rules:
            processed = int(counts_by_rule.get(r.id, 0))
            # Always insert a row (including 0), to mark the run time
            stats_to_add.append(
                EmailStatistic(
                    timestamp=ts,
                    processed=processed,
                    rule_id=r.id,
                    rule_name=r.name or "",
                )
            )

        if stats_to_add:
            self.db.add_all(stats_to_add)
            self.db.commit()

        # Update last_history_id to the latest we saw (or current profile if none)
        self._update_last_history_id(newest_history_id)

    # ---------------------------
    # Label mappings and counting
    # ---------------------------

    @staticmethod
    def _build_label_rule_maps(
            rules: List[EmailRule],
    ) -> Tuple[Dict[str, List[Tuple[int, str]]], Dict[str, List[Tuple[int, str]]]]:
        """
        Returns:
            add_map:    labelId -> list of (rule_id, rule_name) for addLabelIds
            remove_map: labelId -> list of (rule_id, rule_name) for removeLabelIds
        """
        add_map: Dict[str, List[Tuple[int, str]]] = {}
        remove_map: Dict[str, List[Tuple[int, str]]] = {}

        for r in rules:
            for lid in (r.addLabelIds or []):
                add_map.setdefault(lid, []).append((r.id, r.name or ""))
            for lid in (r.removeLabelIds or []):
                remove_map.setdefault(lid, []).append((r.id, r.name or ""))

        return add_map, remove_map

    @staticmethod
    def _accumulate(
            counts_by_rule: Dict[int, int],
            label_to_rules: Dict[str, List[Tuple[int, str]]],
            seen_label_ids: set[str],
    ) -> None:
        """
        For each label in seen_label_ids, increment counts for mapped rules.
        """
        for lid in seen_label_ids:
            for rule_id, _rule_name in label_to_rules.get(lid, []):
                counts_by_rule[rule_id] = counts_by_rule.get(rule_id, 0) + 1

    # ---------------------------
    # Gmail History iteration
    # ---------------------------

    def _iter_history_since(self, start_history_id: int):
        """
        Yields (history_record_dict, latest_history_id_seen) for all history
        items since start_history_id. Pages through results.
        Uses historyTypes labelAdded/labelRemoved only.
        """
        service = self.gmail_client.service
        user_id = "me"
        page_token = None
        latest_seen = start_history_id

        while True:
            req = (
                service.users()
                .history()
                .list(
                    userId=user_id,
                    startHistoryId=start_history_id,
                    historyTypes=["labelAdded", "labelRemoved"],
                    pageToken=page_token,
                    maxResults=500,
                )
            )
            resp = req.execute()
            histories = resp.get("history", [])
            latest_seen = max(latest_seen, int(resp.get("historyId", latest_seen)))

            for h in histories:
                # Each 'h' may also contain its own 'id' (the point-in-time historyId)
                if "id" in h:
                    try:
                        latest_seen = max(latest_seen, int(h["id"]))
                    except Exception:
                        pass
                yield h, latest_seen

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

    # ---------------------------
    # State management
    # ---------------------------

    def _ensure_last_history_initialized(self) -> Optional[int]:
        """
        Ensures we have a stored lastHistoryId.
        - If the state file exists, returns the stored lastHistoryId.
        - If not, initializes it to the current profile.historyId and returns None
          to skip processing on this first run.
        """
        state = self._load_state()
        if state and self.STATE_KEY in state:
            try:
                return int(state[self.STATE_KEY])
            except Exception:
                # If corrupted, reinitialize from profile
                pass

        # Initialize from current profile (no backfill on first run)
        profile = self.gmail_client.service.users().getProfile(userId="me").execute()
        current_history_id = int(profile.get("historyId", 0))
        self._save_state({self.STATE_KEY: current_history_id})
        return None

    def _update_last_history_id(self, latest_history_id: int) -> None:
        """
        Stores the latest processed history id.
        """
        if latest_history_id is None:
            return
        self._save_state({self.STATE_KEY: int(latest_history_id)})

    def _load_state(self) -> Optional[dict]:
        try:
            if os.path.exists(self._state_path):
                with open(self._state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            return None
        return None

    def _save_state(self, state: dict) -> None:
        try:
            with open(self._state_path, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception:
            # Best-effort; avoid crashing the engine if state write fails
            pass