from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import keyring
import json


def get_gmail_client():
    global gmail_client
    if gmail_client is None:
        gmail_client = GmailClient()
    return gmail_client

class GmailClient:
    # If modifying these scopes, delete the file token.pickle.
    SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

    creds = None

    def __init__(self):
        self.service = self._get_gmail_service()

    def _oauth_login(self):
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', self.SCOPES)
            self.creds = flow.run_local_server(port=0)
        elif self.creds.expired and self.creds.refresh_token:
            self.creds.refresh(Request())
        else:
            return

        # Save credentials securely
        keyring.set_password('gmail_api', 'oauth_tokens', self.creds.to_json())


    def _get_gmail_service(self):
        """Gets or refreshes Gmail API service."""
        # Try to get credentials from secure storage
        stored_creds = keyring.get_password('gmail_api', 'oauth_tokens')
        if stored_creds:
            creds_data = json.loads(stored_creds)
            self.creds = Credentials.from_authorized_user_info(creds_data, self.SCOPES)
        else:
            self._oauth_login()

        return build('gmail', 'v1', credentials=self.creds)

    def list_labels(self):
        """Lists all labels in the user's account."""
        self._oauth_login()
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            return labels
        except Exception as e:
            raise Exception(f"Failed to list labels: {e}")

    def create_label(self, name: str, email_id: str = None):
        """Creates a new label and optionally applies it to an email."""
        self._oauth_login()
        try:
            label_object = {
                'name': name,
                'messageListVisibility': 'show',
                'labelListVisibility': 'labelShow'
            }

            created_label = self.service.users().labels().create(
                userId='me',
                body=label_object
            ).execute()

            # If email_id is provided, apply the label to that email
            if email_id:
                self.service.users().messages().modify(
                    userId='me',
                    id=email_id,
                    body={'addLabelIds': [created_label['id']]}
                ).execute()

            return created_label
        except Exception as e:
            raise Exception(f"Failed to create label: {str(e)}")

    def delete_label(self, label_id: str):
        """Deletes a label by its ID."""
        self._oauth_login()
        try:
            self.service.users().labels().delete(
                userId='me',
                id=label_id
            ).execute()
            return True
        except Exception as e:
            raise Exception(f"Failed to delete label: {str(e)}")