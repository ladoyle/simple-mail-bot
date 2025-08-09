from typing import List

from fastapi import Depends
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

    def _upsert_db_rule(self, rules: List[dict]) -> None:
        """Helper method to upsert multiple rules into the local database."""
        self.db.add_all([EmailRule(
            gmail_id=r["id"],
            rule_name=r.get("rule_name", "Unnamed Rule"),
            criteria=json.dumps(r["criteria"]),
            action=json.dumps(r["action"])
        ) for r in rules])
        self.db.commit()

    def _db_delete(self, rules: List[EmailRule]) -> None:
        """Helper method to delete rules from the local database."""
        for rule in rules:
            self.db.delete(rule)
        self.db.commit()

    # ---------------------------
    # Public API used by controller
    # ---------------------------

    def create_rule(self, req: RuleRequest) -> int:
        """
        Create a rule in Gmail, then upsert to DB. Returns DB rule id.
        """

        try:
            # Create in Gmail first (source of truth)
            gmail_rule = self.gmail_client.create_rule(
                criteria=json.loads(req.criteria),
                action=json.loads(req.action)
            )
        except RuntimeError as e:
            raise RuntimeError(f"Failed to create rule in Gmail: {e}")

        # Upsert into DB by rule_name
        rule = self.db.query(EmailRule).filter(
            EmailRule.gmail_id == gmail_rule['id']).first()
        if rule:
            rule.name = req.rule_name
            rule.criteria = req.criteria
            rule.action = req.action
            
        rule = EmailRule(
            gmail_id=gmail_rule['id'],
            rule_name=req.rule_name,
            criteria=req.criteria,
            action=req.action
            )
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete_rule(self, rule_id: int) -> bool:
        """
        Delete a rule: remove from Gmail first, then from DB. Returns True if deleted, False if not found.
        """
        db_rule = self.db.query(EmailRule).filter(EmailRule.id == rule_id).first()
        if not db_rule:
            return False

        try:
            # Delete from Gmail first (source of truth)
            self.gmail_client.delete_rule(
                rule_id=db_rule.gmail_id
            )
        except RuntimeError as e:
            raise RuntimeError(f"Failed to delete rule from Gmail: {e}")

        # Delete from DB
        self._db_delete([db_rule])

        return True

    def list_rules(self) -> List[EmailRule]:
        """
        List rules by syncing from Gmail first (Gmail is the gold standard)
        and returning the DB rows.
        """
        gmail_rules = self.gmail_client.list_rules()
        # map by rule_name (assumed unique)
        gmail_map = {r["id"]: r for r in gmail_rules}

        # Fetch local rules
        local_rules = self.db.query(EmailRule).all()
        local_map = {r.gmail_id: r for r in local_rules}

        # Upsert all Gmail rules
        self._upsert_db_rule(
            [r for r in gmail_rules if r["id"] not in local_map]
            )

        # Remove DB rules not present in Gmail
        self._db_delete(
            [r for r in local_rules if r.gmail_id not in gmail_map]
        )

        return self.db.query(EmailRule).order_by(EmailRule.rule_name.asc()).all()

