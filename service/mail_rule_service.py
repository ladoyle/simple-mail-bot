import logging as log
from typing import List, Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import database
from models.mail_bot_schemas import RuleRequest
from backend.database import EmailRule
from backend.gmail_client import GmailClient, get_gmail_client
import json

mail_rule_service = None


def get_rule_service(
        db: Session = Depends(database.get_db),
        gmail_client: GmailClient = Depends(get_gmail_client)
):
    global mail_rule_service
    if mail_rule_service is None:
        mail_rule_service = MailRuleService(db_session=db, gmail_client=gmail_client)
    return mail_rule_service


class MailRuleService:
    """
    Service that manages rules in Gmail and keeps the local DB in sync.
    Gmail is the source of truth:
    - On create/update/delete: perform the operation in Gmail first, then persist to DB.
    - On read/list: fetch from Gmail and reconcile DB.
    """

    def __init__(self, db_session: Session, gmail_client: GmailClient):
        self.db: Session = db_session
        self.gmail_client = gmail_client
       
    # ---------------------------
    # Internal utilities
    # ---------------------------

    def _upsert_db_rule(self, user_email: str, rules: list[dict]) -> None:
        """Helper method to upsert multiple rules into the local database."""
        log.warning(f"Upserting {len(rules)} rules into DB during sync")
        self.db.add_all([EmailRule(
            email_address=user_email,
            gmail_id=r["id"],
            rule_name=r.get("rule_name", "Unnamed Rule"),
            criteria=r.get("criteria", ''),
            addLabelIds=r["action"].get("addLabelIds", []),
            removeLabelIds=r["action"].get("removeLabelIds", []),
            forward=r["action"].get("forward", "")
        ) for r in rules])
        self.db.commit()

    def _db_delete(self, rules: list[EmailRule]) -> None:
        """Helper method to delete rules from the local database."""
        log.warning(f"Deleting {len(rules)} rules from DB during sync")
        for rule in rules:
            self.db.delete(rule)
        self.db.commit()

    # ---------------------------
    # Public API used by controller
    # ---------------------------

    def create_rule(self, user_email: str, req: RuleRequest) -> EmailRule:
        """
        Create a rule in Gmail, then upsert to DB. Returns DB rule id.
        """

        try:
            # Create in Gmail first (source of truth)
            gmail_rule = self.gmail_client.create_filter(
                criteria=json.loads(req.criteria),
                actions={
                    'addLabelIds': req.addLabelIds,
                    'removeLabelIds': req.removeLabelIds,
                    'forward': req.forward
                },
                user_email=user_email
            )
        except Exception as e:
            raise RuntimeError(f"Failed to create rule in Gmail: {e}")

        # Upsert into DB by rule_name
        db_rule = EmailRule(
            email_address=user_email,
            gmail_id=gmail_rule['id'],
            rule_name=req.rule_name,
            criteria=req.criteria,
            action=req.action
            )
        self.db.add(db_rule)
        self.db.commit()
        self.db.refresh(db_rule)
        return db_rule

    def delete_rule(self, user_email: str, rule_id: int) -> bool:
        """
        Delete a rule: remove from Gmail first, then from DB. Returns True if deleted, False if not found.
        """
        db_rule: Optional[EmailRule, None] = self.db.get(EmailRule, rule_id)
        if not db_rule:
            return False

        try:
            # Delete from Gmail first (source of truth)
            self.gmail_client.delete_filter(
                filter_id=db_rule.gmail_id,
                user_email=user_email
            )
        except Exception as e:
            raise RuntimeError(f"Failed to delete rule from Gmail: {e}")

        # Delete from DB
        self._db_delete([db_rule])

        return True

    def list_rules(self, user_email: str) -> List[EmailRule]:
        """
        List rules by syncing from Gmail first (Gmail is the gold standard)
        and returning the DB rows.
        """
        try:
            gmail_rules = self.gmail_client.list_filters(user_email)
            # map by rule_name (assumed unique)
            gmail_map = {r["id"]: r for r in gmail_rules}
            log.info(f"Fetched {len(gmail_map)} rules from Gmail")
        except Exception as e:
            raise RuntimeError(f"Failed to list rules from Gmail: {e}")

        # Fetch local rules
        local_rules = self.db.execute(
            select(EmailRule).where(EmailRule.email_address == user_email)
        ).scalars().all()
        local_map = {r.gmail_id: r for r in local_rules}
        log.info(f"Fetched {len(local_map)} rules from DB")

        # Upsert all Gmail rules
        self._upsert_db_rule(
            user_email,
            [r for r in gmail_rules if r["id"] not in local_map]
            )

        # Remove DB rules not present in Gmail
        self._db_delete(
            [r for r in local_rules if r.gmail_id not in gmail_map]
        )
        return list(self.db.execute(
            select(EmailRule).where(EmailRule.email_address == user_email).order_by(EmailRule.name)
        ).scalars().all())

