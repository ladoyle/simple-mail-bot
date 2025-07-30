# service/mail_rule_service.py

import logging as log
from sqlalchemy.orm import Session
from backend.database import SessionLocal, EmailStatistic, EmailRule
# from backend.api_client import GmailClient  # Placeholder for Gmail API client

class MailService:
    def __init__(self):
        self.db: Session = SessionLocal()
        # self.gmail_client = GmailClient()  # Initialize Gmail API client here

    def add_rule(self, rule_name, condition, action):
        # todo
        #  1. Validate the Rule
        #  2. Check if rule already exists, log update message if yes
        #  3. Add the rule to the database
        #  4. Call Gmail API to create the rule
        existing_rule = self.db.query(EmailRule).filter(rule_name).first()
        if existing_rule:
            log.warning("Rule with name '%s' already exists. Updating the rule.", rule_name)
        rule = EmailRule(rule_name=rule_name, condition=condition, action=action)
        self.db.add(rule)
        self.db.commit()
        # self.gmail_client.create_rule(rule_name, condition, action)  # Placeholder for Gmail API call
        log.info("Rule '%s' added successfully.", rule_name)
        return rule

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


    def label_email(self, email_id, label):
        # Placeholder for Gmail API call to label an email
        # self.gmail_client.label_email(email_id, label)
        self.increment_processed()
        return True

    def __del__(self):
        if hasattr(self, "db"):
            self.db.close()