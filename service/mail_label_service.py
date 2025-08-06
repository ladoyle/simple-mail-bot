from fastapi import Depends
from sqlalchemy.orm import Session

from models.mail_bot_schemas import LabelRequest
from backend.database import EmailLabel, get_db
from backend.gmail_client import GmailClient, get_gmail_client

def get_label_service(
    db: Session = Depends(get_db),
    gmail_client: GmailClient = Depends(get_gmail_client)
):
    global mail_label_service
    if mail_label_service is None:
        mail_label_service = MailLabelService(db_session=db, gmail_client=gmail_client)
    return mail_label_service

class MailLabelService:
    def __init__(self, db_session: Session, gmail_client: GmailCLient):
        self.db = db_session
        self.gmail_client = gmail_client

    def __del__(self):
        if hasattr(self, "db"):
            self.db.close()

    def _db_add(self, labels: list[str]):
        """Helper method to add labels to the local database."""
        self.db.add_all([EmailLabel(name=lbl) for lbl in labels])
        self.db.commit()

    def _db_delete(self, labels: list[str]):
        """Helper method to delete labels from the local database."""
        existing_labels = self.db.query(EmailLabel).filter(EmailLabel.name.in_(labels)).all()
        for label in existing_labels:
            self.db.delete(label)
        self.db.commit()

    def list_labels(self):
        try:
            # Get from Gmail (golden source)
            gmail_labels = self.gmail_client.list_labels()
            gmail_label_names = {lbl['name'] for lbl in gmail_labels}
        except Exception as e:
            raise RuntimeError(f"Failed to fetch labels from Gmail: {e}")

        # Fetch all local labels
        local_labels = self.db.query(EmailLabel).all()
        local_label_names = {label.name for label in local_labels}

        # Add new labels from Gmail to DB
        new_labels = [lbl for lbl in gmail_label_names if lbl not in local_label_names]
        self._db_add(new_labels)

        # Delete labels from DB that are not in Gmail
        bad_labels = [lbl for lbl in local_label_names if lbl not in gmail_label_names]
        self._db_delete(bad_labels)

        # Return synced labels from db
        local_labels = self.db.query(EmailLabel).all()
        return local_labels

    def create_label(self, req: LabelRequest):
        try:
            # Create label in Gmail (golden source)
            gmail_label = self.gmail_client.create_label(req.name, req.email_id)
        except Exception as e:
            raise RuntimeError(f"Failed to create label in Gmail: {e}")

        # Store in local DB
        label = EmailLabel(name=gmail_label['name'])
        self.db.add(label)
        self.db.commit()
        self.db.refresh(label)
        return label.id

    def delete_label(self, label_id: int):
        label = self.db.query(EmailLabel).filter(EmailLabel.id == label_id)
        if not label:
            return False

        try:
            # Delete from Gmail
            self.gmail_client.delete_label(label.gmail_id)
        except Exception as e:
            raise RuntimeError(f"Failed to delete label from Gmail: {e}")

        # Delete from local DB
        self.db.delete(label)
        self.db.commit()
        return True
