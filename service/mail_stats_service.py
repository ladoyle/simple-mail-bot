# Python
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import database
from backend.database import EmailStatistic
from backend.gmail_client import GmailClient, get_gmail_client

mail_stats_service = None


def get_stats_service(
        db: Session = Depends(database.get_db),
        gmail_client: GmailClient = Depends(get_gmail_client)
):
    global mail_stats_service
    if mail_stats_service is None:
        mail_stats_service = MailStatsService(db_session=db, gmail_client=gmail_client)
    return mail_stats_service


class MailStatsService:
    """
    Service that provides analytics on the numbers of emails processed by the bot.
    Analytics are stored in the local DB (EmailStatistic).
    """

    def __init__(self, db_session: Session, gmail_client: GmailClient):
        self.db: Session = db_session
        self.gmail_client = gmail_client

    # ---------------------------
    # Processed counters (DB-based)
    # ---------------------------

    def get_total_processed(self, user_email: str, rule_id: int) -> int:
        return self._sum_processed(email_address=user_email, rule_id=rule_id)

    def get_daily_processed(self, user_email: str, rule_id: int) -> int:
        """
        Sum processed for the last 24 hours (rolling window).
        """
        now_ts = self._now_utc_timestamp()
        start_ts = now_ts - 24 * 60 * 60
        return self._sum_processed(email_address=user_email, rule_id=rule_id, start_ts=start_ts, end_ts=now_ts)

    def get_weekly_processed(self, user_email: str, rule_id: int) -> int:
        start_ts = self._start_of_week_utc_timestamp()
        return self._sum_processed(email_address=user_email, rule_id=rule_id, start_ts=start_ts)

    def get_monthly_processed(self, user_email: str, rule_id: int) -> int:
        start_ts = self._start_of_month_utc_timestamp()
        return self._sum_processed(email_address=user_email, rule_id=rule_id, start_ts=start_ts)

    def _sum_processed(self, email_address: str, rule_id: int, start_ts: Optional[int] = None, end_ts: Optional[int] = None) -> int:
        """
        Sum EmailStatistic.processed for a rule and email address within an optional [start_ts, end_ts) range.
        Timestamps are stored as integer epoch seconds (assumed UTC).
        """
        q = self.db.query(func.coalesce(func.sum(EmailStatistic.processed), 0)).filter(
            EmailStatistic.rule_id == rule_id,
            EmailStatistic.email_address == email_address
        )
        if start_ts is not None:
            q = q.filter(EmailStatistic.timestamp >= start_ts)
        if end_ts is not None:
            q = q.filter(EmailStatistic.timestamp < end_ts)
        total = q.scalar()
        return int(total or 0)

    # ---------------------------
    # Time helpers
    # ---------------------------

    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)

    def _now_utc_timestamp(self) -> int:
        return int(self._now_utc().timestamp())

    def _start_of_week_utc_timestamp(self) -> int:
        """
        Start of current week (Mon 00:00 UTC) using now
        """
        now = self._now_utc()
        start_of_week_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        return int(start_of_week_date.timestamp())

    def _start_of_month_utc_timestamp(self) -> int:
        now = self._now_utc()
        som = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return int(som.timestamp())

    # ---------------------------
    # Read/Unread counters (Gmail-based)
    # ---------------------------

    def get_unread_count(self, user_email: str) -> int:
        """
        Retrieve unread count directly from Gmail via the client.
        """
        try:
            return self.gmail_client.get_unread_count(user_email)
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve unread emails count: {e}")

    def get_read_count(self, user_email) -> int:
        """
        Retrieve read count as total - unread, both from the Gmail client.
        """
        try:
            total = self.gmail_client.get_total_count(user_email)
            unread = self.gmail_client.get_unread_count(user_email)
            read = total - unread
            return read if read >= 0 else 0
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve read emails count: {e}")