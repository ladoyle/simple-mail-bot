# service/mail_service.py

from sqlalchemy.orm import Session
from backend.database import SessionLocal, EmailStatistic, EmailRule
# from backend.api_client import GmailClient  # Placeholder for Gmail API client

class MailService:
    def __init__(self):
        self.db: Session = SessionLocal()
        # self.gmail_client = GmailClient()  # Initialize Gmail API client here

    def get_statistics(self):
        stats = self.db.query(EmailStatistic).first()
        return stats

    def increment_processed(self):
        stats = self.db.query(EmailStatistic).first()
        if stats:
            stats.processed += 1
            self.db.commit()

    def get_unread_count(self):
        stats = self.db.query(EmailStatistic).first()
        return stats.unread if stats else 0

    def get_read_count(self):
        stats = self.db.query(EmailStatistic).first()
        return stats.read if stats else 0

    def add_rule(self, rule_name, condition, action):
        rule = EmailRule(rule_name=rule_name, condition=condition, action=action)
        self.db.add(rule)
        self.db.commit()
        return rule

    def label_email(self, email_id, label):
        # Placeholder for Gmail API call to label an email
        # self.gmail_client.label_email(email_id, label)
        self.increment_processed()
        return True

    def __del__(self):
        if hasattr(self, "db"):
            self.db.close()