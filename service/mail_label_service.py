from typing import Optional

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend import database
from models.mail_bot_schemas import LabelRequest
from backend.database import EmailLabel
from backend.gmail_client import GmailClient, get_gmail_client

mail_label_service = None


def get_label_service(
        db: Session = Depends(database.get_db),
        gmail_client: GmailClient = Depends(get_gmail_client)
):
    global mail_label_service
    if mail_label_service is None:
        mail_label_service = MailLabelService(db_session=db, gmail_client=gmail_client)
    return mail_label_service


class MailLabelService:
    def __init__(self, db_session: Session, gmail_client: GmailClient):
        self.db = db_session
        self.gmail_client = gmail_client

    def _upsert_db(self, labels: list[dict]):
        """Helper method to add labels to the local database."""
        self.db.add_all(
            [EmailLabel(gmail_id=lbl['id'], name=lbl['name']) for lbl in labels]
        )
        self.db.commit()

    def _db_delete(self, labels: list[EmailLabel]):
        """Helper method to delete labels from the local database."""
        for label in labels:
            self.db.delete(label)
        self.db.commit()

    def list_labels(self) -> list[EmailLabel]:
        try:
            # Get from Gmail (golden source)
            gmail_labels = self.gmail_client.list_labels()
            gmail_label_map = {lbl['id']: lbl for lbl in gmail_labels}
        except Exception as e:
            raise RuntimeError(f"Failed to fetch labels from Gmail: {e}")

        # Fetch all local labels
        local_labels = self.db.execute(select(EmailLabel)).scalars().all()
        local_label_map = {label.gmail_id: label for label in local_labels}

        # Add new labels from Gmail to DB
        self._upsert_db([lbl for gid, lbl in gmail_label_map.items() if gid not in local_label_map])

        # Delete labels from DB that are not in Gmail
        self._db_delete([lbl for lbl in local_labels if lbl.gmail_id not in gmail_label_map])

        # Return synced labels from db
        return list(self.db.execute(select(EmailLabel).order_by(EmailLabel.name)).scalars().all())

    def create_label(self, req: LabelRequest):
        try:
            # Create label in Gmail (golden source)
            gmail_label = self.gmail_client.create_label(req.name)
        except Exception as e:
            raise RuntimeError(f"Failed to create label in Gmail: {e}")

        # Store in local DB
        label = EmailLabel(name=gmail_label['name'], gmail_id=gmail_label['id'])
        self.db.add(label)
        self.db.commit()
        self.db.refresh(label)
        return label.id

    def delete_label(self, label_id: int):
        label: Optional[EmailLabel, None] = self.db.get(EmailLabel, label_id)
        if not label:
            return False

        try:
            # Delete from Gmail
            self.gmail_client.delete_label(label.gmail_id)
        except Exception as e:
            raise RuntimeError(f"Failed to delete label from Gmail: {e}")

        # Delete from local DB
        self._db_delete([label])
        return True
