from __future__ import annotations

import logging as log
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import database
from backend.database import EmailRule, EmailStatistic
from backend.gmail_client import GmailClient, get_gmail_client

history_engine_singleton = None


def get_history_engine_service(
        db: Session = Depends(database.get_db),
        gmail_client: GmailClient = Depends(get_gmail_client),
):
    """
    Dependency to get a singleton MailHistoryEngineService.
    Call start() once on application boot to launch the scheduler.
    """
    global history_engine_singleton
    if history_engine_singleton is None:
        history_engine_singleton = HistoryEngine(db_session=db, gmail_client=gmail_client)
    return history_engine_singleton


class HistoryEngine:
    """
    History Engine:
    - At 4:00 AM (UTC) every day, aggregates Gmail history changes for all authorized users.
    - For each user, builds a mapping from EmailRule labelIds to rule_id.
    - Uses Gmail client to pull history and count messages that had those labels added/removed.
    - Persists a row in EmailStatistic with (timestamp, processed, rule_id, rule_name, email_address).
    - Updates each user's last_history_id after processing.
    """

    def __init__(self, db_session: Session, gmail_client: GmailClient):
        log.debug("Initializing mail history engine")
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
        log.info("Starting mail history engine")
        if self._task and not self._task.done():
            log.warning("Mail history engine already running")
            return
        self._task = asyncio.create_task(self._scheduler_loop(), name="mail-history-engine-4am")

    def stop(self) -> None:
        """
        Cancels the background scheduler, if running.
        """
        log.info("Stopping mail history engine")
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
                log.info(f"Sleeping until next 4:00 AM UTC: {sleep_seconds} seconds")
                await asyncio.sleep(sleep_seconds)
                await self.run_once()
        except asyncio.CancelledError:
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
        Performs an aggregation cycle for each user in db:
        - Load rules and build labelId -> rule_id mapping.
        - Fetch Gmail history via gmail_client.list_history.
        - For each history entry, count messages whose label changes match a rule's labels.
          Each message is counted at most once per rule for this run.
        - Insert EmailStatistic totals with current timestamp.
        """
        log.info(f"Loading mail history stats at {datetime.now(timezone.utc)}")

        # Query all authorized users
        users = self.db.execute(select(database.AuthorizedUsers)).scalars().all()
        if not users:
            return

        stats_to_add: List[EmailStatistic] = []

        for user in users:
            user_email = user.email
            last_history_id = user.last_history_id

            # Fetch rules for this user only
            rules = self.db.execute(
                select(EmailRule).where(EmailRule.email_address == user_email)
            ).scalars().all()
            if not rules:
                continue

            label_to_rule_ids, rule_names = self._build_label_to_rule_ids(list(rules))

            try:
                updated_history_id, histories = self.gmail_client.list_history(
                    user_email=user_email,
                    history_id=last_history_id,
                    history_types=["labelAdded", "labelRemoved"]
                )
            except Exception as e:
                log.error(f"Failed to fetch Gmail history for {user_email}: {e}")
                continue

            rule_to_message_ids: Dict[int, Set[str]] = {r.id: set() for r in rules}

            for history in histories:
                for added in history.get("labelsAdded", []):
                    msg = (added.get("message") or {})
                    mid = msg.get("id")
                    if not mid:
                        continue
                    label_ids = added.get("labelIds") or []
                    self._collect_for_event(rule_to_message_ids, label_to_rule_ids, label_ids, mid)
                for removed in history.get("labelsRemoved", []):
                    msg = (removed.get("message") or {})
                    mid = msg.get("id")
                    if not mid:
                        continue
                    label_ids = removed.get("labelIds") or []
                    self._collect_for_event(rule_to_message_ids, label_to_rule_ids, label_ids, mid)

            ts = int(datetime.now(timezone.utc).timestamp())
            for rid, mids in rule_to_message_ids.items():
                processed = len(mids)
                stats_to_add.append(
                    EmailStatistic(
                        timestamp=ts,
                        processed=processed,
                        rule_id=rid,
                        rule_name=rule_names.get(rid, ""),
                        email_address=user_email,
                    )
                )

            user.last_history_id = updated_history_id
            self.db.commit()

        if stats_to_add:
            self.db.add_all(stats_to_add)
            self.db.commit()

    @staticmethod
    def _build_label_to_rule_ids(
            rules: List[EmailRule],
    ) -> tuple[Dict[str, Set[int]], Dict[int, str]]:
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
        for lid in label_ids:
            for rid in label_to_rule_ids.get(lid, set()):
                rule_to_message_ids.setdefault(rid, set()).add(message_id)