from typing import List

from fastapi import Depends
from sqlalchemy.orm import Session

from backend import database
from models.mail_bot_schemas import RuleRequest
from backend.database import EmailRule
from backend.gmail_client import GmailClient, get_gmail_client

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
    # Public API used by controller
    # ---------------------------

    def create_rule(self, req: RuleRequest) -> int:
        """
        Create a rule in Gmail, then upsert to DB. Returns DB rule id.
        """

        # Create in Gmail first (source of truth)
        self.gmail_client.create_rule(
            rule_name=req.rule_name,
            condition=req.condition,
            action=req.action,
        )

        # Upsert into DB by rule_name
        db_rule = self._upsert_db_rule_by_name(
            rule_name=req.rule_name,
            condition=req.condition,
            action=req.action,
        )

        return db_rule.id

    def delete_rule(self, rule_id: int) -> bool:
        """
        Delete a rule: remove from Gmail first, then from DB. Returns True if deleted, False if not found.
        """
        db_rule = self.db.query(EmailRule).filter(EmailRule.id == rule_id).first()
        if not db_rule:
            return False

        # Delete from Gmail first (source of truth)
        self.gmail_client.delete_rule(
            rule_name=db_rule.rule_name,
            condition=db_rule.condition,
            action=db_rule.action,
        )

        # Delete from DB
        self.db.delete(db_rule)
        self.db.commit()

        return True

    def list_rules(self) -> List[EmailRule]:
        """
        List rules by syncing from Gmail first (Gmail is the gold standard)
        and returning the DB rows.
        """
        self.sync_from_gmail()
        return self.db.query(EmailRule).order_by(EmailRule.rule_name.asc()).all()

    # ---------------------------
    # Sync helpers
    # ---------------------------

    def sync_from_gmail(self) -> None:
        """
        Pull all rules from Gmail and synchronize the local DB:
        - Upsert all Gmail rules into DB (by rule_name).
        - Remove any DB rules that don't exist in Gmail.
        """
        gmail_rules = self.gmail_client.list_rules()

        # Index by rule_name (assumed unique)
        gmail_index = {r["rule_name"]: r for r in gmail_rules}

        # Upsert all Gmail rules
        for r in gmail_rules:
            self._upsert_db_rule_by_name(
                rule_name=r["rule_name"],
                condition=r.get("condition"),
                action=r.get("action"),
            )

        # Remove DB rules not present in Gmail
        db_rules = self.db.query(EmailRule).all()
        for db_rule in db_rules:
            if db_rule.rule_name not in gmail_index:
                self.db.delete(db_rule)

        self.db.commit()

    # ---------------------------
    # Internal utilities
    # ---------------------------

    def _upsert_db_rule_by_name(self, rule_name: str, condition, action) -> EmailRule:
        existing = self.db.query(EmailRule).filter(EmailRule.rule_name == rule_name).first()
        if existing:
            existing.condition = condition
            existing.action = action
            self.db.commit()
            return existing

        rule = EmailRule(rule_name=rule_name, condition=condition, action=action)
        self.db.add(rule)
        self.db.commit()
        return rule

