from typing import Optional

from fastapi import Depends

from backend import database
from backend.database import AuthorizedUsers
from sqlalchemy.orm import Session

from backend.gmail_client import GmailClient, get_gmail_client

mail_oauth_service = None


def get_oauth_service(
        db: Session = Depends(database.get_db),
        gmail_client: GmailClient = Depends(get_gmail_client)
):
    global mail_oauth_service
    if mail_oauth_service is None:
        mail_oauth_service = MailOAuthService(db_session=db, gmail_client=gmail_client)
    return mail_oauth_service


class MailOAuthService:
    def __init__(self, gmail_client, db_session: Session):
        self.gmail_client = gmail_client
        self.db = db_session

    def _add_user(self, email):
        self.db.add(AuthorizedUsers(email=email))
        self.db.commit()

    def get_authorization_url(self):
        try:
            return self.gmail_client.get_authorization_url()
        except Exception as e:
            raise RuntimeError(f"Failed to get authorization URL: {e}")

    def handle_callback(self, code) -> tuple[str, str]:
        try:
            user_email, access_token = self.gmail_client.exchange_code_for_token(code)
        except Exception as e:
            raise RuntimeError(f"Failed to exchange code for token: {e}")
        self._add_user(user_email)
        return user_email, access_token

    def remove_user(self, email):
        user: Optional[AuthorizedUsers, None] = self.db.get(AuthorizedUsers, email)
        if not user:
            return False

        try:
            # Delete token from Gmail Client
            self.gmail_client.remove_user(email)
        except Exception as e:
            raise RuntimeError(f"Failed to delete token from Gmail: {e}")

        # Delete from local DB
        self.db.delete(user)
        self.db.commit()
        return True