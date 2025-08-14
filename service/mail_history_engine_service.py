from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Optional

from fastapi import Depends
from sqlalchemy import select
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
    - Builds a mapping from EmailRule labelIds to rule_id.
    - Uses Gmail client (which maintains history state) to pull history and count
      messages that had those labels added/removed.
    - Persists a row in EmailStatistic with (timestamp, processed, rule_id, rule_name).
    """

    def __init__(self, db_session: Session, gmail_client: GmailClient):
        self.db: Session = db_session
        self.gmail_client = gmail_client
        self._task: Optional[asyncio.Task] = None

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
        - Load rules and build labelId -> rule_id mapping.
        - Fetch Gmail history via gmail_client.list_history (client maintains state).
        - For each history entry, count messages whose label changes match a rule's labels.
          Each message is counted at most once per rule for this run.
        - Insert EmailStatistic totals with current timestamp.
        """
        # 1) Load rules
        rules = self.db.execute(select(EmailRule)).scalars().all()
        if not rules:
            return

        # 2) Build mapping: labelId -> set(rule_id)
        label_to_rule_ids, rule_names = self._build_label_to_rule_ids(list(rules))

        # 3) Get history entries from the client (it maintains startHistoryId internally)
        try:
            histories: List[dict] = self.gmail_client.list_history(history_types=["labelAdded", "labelRemoved"])
        except Exception as e:
            raise RuntimeError(f"Failed to fetch Gmail history: {e}")

        # 4) For each rule, track unique message ids processed in this run
        rule_to_message_ids: Dict[int, Set[str]] = {r.id: set() for r in rules}

        # 5) Accumulate based on labelsAdded / labelsRemoved
        for history in histories:
            # labelsAdded: [{ "message": { "id": ... }, "labelIds": [...] }, ...]
            for added in history.get("labelsAdded", []):
                msg = (added.get("message") or {})
                mid = msg.get("id")
                if not mid:
                    continue
                label_ids = added.get("labelIds") or []
                self._collect_for_event(rule_to_message_ids, label_to_rule_ids, label_ids, mid)

            # labelsRemoved: same structure
            for removed in history.get("labelsRemoved", []):
                msg = (removed.get("message") or {})
                mid = msg.get("id")
                if not mid:
                    continue
                label_ids = removed.get("labelIds") or []
                self._collect_for_event(rule_to_message_ids, label_to_rule_ids, label_ids, mid)

        # 6) Persist totals with current timestamp (count unique messages per rule)
        ts = int(datetime.now(timezone.utc).timestamp())
        stats_to_add: List[EmailStatistic] = []
        for r in rules:
            processed = len(rule_to_message_ids.get(r.id, set()))
            stats_to_add.append(
                EmailStatistic(
                    timestamp=ts,
                    processed=processed,
                    rule_id=r.id,
                    rule_name=rule_names.get(r.id, r.name or ""),
                )
            )

        if stats_to_add:
            self.db.add_all(stats_to_add)
            self.db.commit()

        # The gmail_client is expected to update its stored history id internally.

    # ---------------------------
    # Mapping and accumulation
    # ---------------------------

    @staticmethod
    def _build_label_to_rule_ids(
            rules: List[EmailRule],
    ) -> tuple[Dict[str, Set[int]], Dict[int, str]]:
        """
        Build a single mapping of labelId -> set(rule_id) combining both addLabelIds and removeLabelIds.
        Also returns a map of rule_id -> rule_name for storage.
        """
        label_to_rule_ids: Dict[str, Set[int]] = {}
        rule_names: Dict[int, str] = {}

        for r in rules:
            rule_names[r.id] = r.name or ""
            for lid in (r.addLabelIds or []):
                label_to_rule_ids.setdefault(lid, set()).add(r.id)
            for lid in (r.removeLabelIds or []):
                label_to_rule_ids.setdefault(lid, set()).add(r.id)

        return label_to_rule_ids, rule_names

    @staticmethod
    def _collect_for_event(
            rule_to_message_ids: Dict[int, Set[str]],
            label_to_rule_ids: Dict[str, Set[int]],
            label_ids: List[str],
            message_id: str,
    ) -> None:
        """
        For the given message and its associated label_ids, mark the message as processed
        for every rule that references any of those label ids. Deduplicates per rule.
        """
        for lid in label_ids:
            for rid in label_to_rule_ids.get(lid, set()):
                rule_to_message_ids.setdefault(rid, set()).add(message_id)