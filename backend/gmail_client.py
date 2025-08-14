from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import keyring
import json

gmail_client = None


def get_gmail_client():
    global gmail_client
    if gmail_client is None:
        gmail_client = GmailClient()
    return gmail_client


class GmailClient:
    # ----------------------------
    ## Gmail OAuth integration
    # ----------------------------

    # If modifying these scopes, delete the file token.pickle.
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.labels',  # For creating/modifying labels
        'https://www.googleapis.com/auth/gmail.modify',  # For modifying emails (applying labels)
        'https://www.googleapis.com/auth/gmail.settings.basic'  # Required for filter management
    ]

    creds = None

    def __init__(self):
        self.service = self._get_gmail_service()

    def _oauth_login(self):
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', self.SCOPES)
            self.creds = flow.run_local_server(port=8000)
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

        return build('gmail', 'v1',
                     credentials=self.creds,
                     discoveryServiceUrl="https://gmail.googleapis.com/$discovery/rest?version=v1")

    # -------------
    ## Labels
    # -------------

    def _list_labels(self):
        """Lists all labels in the user's account."""
        results = self.service.users().labels().list(userId='me').execute()
        return results.get('labels', [])

    def list_labels(self):
        """Lists all labels in the user's account."""
        self._oauth_login()
        try:
            return self._list_labels()
        except Exception as e:
            raise Exception(f"Failed to list labels: {e}")

    def create_label(self, name: str):
        """Creates a new label."""
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

            return created_label
        except Exception as e:
            raise Exception(f"Failed to create label: {e}")

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

    # --------------
    ## Filters
    # --------------

    def create_filter(self, criteria: dict, actions: dict):
        """
        Create a Gmail filter

        Args:
            criteria (dict): Filter criteria like:
                {
                    'from': 'sender@example.com',
                    'to': 'recipient@example.com',
                    'subject': 'subject text',
                    'query': 'has:attachment' # or other search operators
                }
            actions (dict): Actions to take like:
                {
                    'addLabelIds': ['Label_123'],
                    'removeLabelIds': ['INBOX'],
                    'forward': 'forward@example.com'
                }
        """
        self._oauth_login()
        try:
            filter_object = {
                'criteria': criteria,
                'action': actions
            }

            result = self.service.users().settings().filters().create(
                userId='me',
                body=filter_object
            ).execute()
            return result
        except Exception as e:
            raise Exception(f"Failed to create filter: {str(e)}")

    def list_filters(self):
        """List all filters in the Gmail account."""
        self._oauth_login()
        try:
            results = self.service.users().settings().filters().list(
                userId='me'
            ).execute()
            return results.get('filter', [])
        except Exception as e:
            raise Exception(f"Failed to list filters: {str(e)}")

    def delete_filter(self, filter_id: str):
        """Delete a specific filter by ID."""
        self._oauth_login()
        try:
            self.service.users().settings().filters().delete(
                userId='me',
                id=filter_id
            ).execute()
            return True
        except Exception as e:
            raise Exception(f"Failed to delete filter: {str(e)}")

    def get_unread_count(self) -> int:
        """
        Return the number of unread messages using the UNREAD system label.
        Leverages labels.get to read messagesUnread for the UNREAD label.
        """
        self._oauth_login()
        try:
            all_labels = self._list_labels()
            unread_label_id = [lid for lid in all_labels if lid['id'] == 'UNREAD'][0]
            label = self.service.users().labels().get(userId='me', id=unread_label_id).execute()
            return int(label.get('messagesUnread', 0))
        except Exception as e:
            raise Exception(f"Failed to retrieve unread count from Gmail: {e}")

    def get_total_count(self) -> int:
        """
        Return the total number of messages using the user profile endpoint.
        """
        self._oauth_login()
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return int(profile.get('messagesTotal', 0))
        except Exception as e:
            raise Exception(f"Failed to retrieve total message count from Gmail: {e}")