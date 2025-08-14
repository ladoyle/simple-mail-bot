from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import keyring
import json
import logging as log

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
    user_id = 'me'

    def __init__(self):
        self.service = self._get_gmail_service()
        # In-memory history cursor (None means not initialized yet)
        self._last_history_id = ""

    def _oauth_login(self):
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds:
            log.info("No OAuth tokens found, running OAuth login flow.")
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', self.SCOPES)
            self.creds = flow.run_local_server(port=8000)
        elif self.creds.expired and self.creds.refresh_token:
            log.info("OAuth tokens expired, refreshing.")
            self.creds.refresh(Request())
        else:
            return

        # Save credentials securely
        keyring.set_password('gmail_api', 'oauth_tokens', self.creds.to_json())

    def _get_gmail_service(self):
        """Gets or refreshes Gmail API service."""
        # Try to get credentials from secure storage
        log.info("Retrieving OAuth tokens from keyring.")
        stored_creds = keyring.get_password('gmail_api', 'oauth_tokens')
        if stored_creds:
            creds_data = json.loads(stored_creds)
            self.creds = Credentials.from_authorized_user_info(creds_data, self.SCOPES)
        else:
            self._oauth_login()

        log.info("Initializing Gmail API service.")
        return build('gmail', 'v1',
                     credentials=self.creds,
                     discoveryServiceUrl="https://gmail.googleapis.com/$discovery/rest?version=v1")

    # -------------
    ## Labels
    # -------------

    def _list_labels(self):
        """Lists all labels in the user's account."""
        log.info("Retrieving labels from Gmail API.")
        results = self.service.users().labels().list(userId=self.user_id).execute()
        log.info(f"Retrieved {len(results.get('labels', []))} labels from Gmail.")
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

            log.info(f"Creating label '{name}' in Gmail API.")
            created_label = self.service.users().labels().create(
                userId=self.user_id,
                body=label_object
            ).execute()

            return created_label
        except Exception as e:
            raise Exception(f"Failed to create label: {e}")

    def delete_label(self, label_id: str):
        """Deletes a label by its ID."""
        self._oauth_login()
        try:
            log.warning(f"Deleting label '{label_id}' from Gmail API.")
            self.service.users().labels().delete(
                userId=self.user_id,
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

            log.info(f"Creating filter in Gmail API.")
            result = self.service.users().settings().filters().create(
                userId=self.user_id,
                body=filter_object
            ).execute()
            return result
        except Exception as e:
            raise Exception(f"Failed to create filter: {str(e)}")

    def list_filters(self):
        """List all filters in the Gmail account."""
        self._oauth_login()
        try:
            log.info(f"Listing filters in Gmail API.")
            results = self.service.users().settings().filters().list(
                userId=self.user_id
            ).execute()
            log.info(f"Retrieved {len(results.get('filter', []))} filters from Gmail.")
            return results.get('filter', [])
        except Exception as e:
            raise Exception(f"Failed to list filters: {str(e)}")

    def delete_filter(self, filter_id: str):
        """Delete a specific filter by ID."""
        self._oauth_login()
        try:
            log.warning(f"Deleting filter '{filter_id}' from Gmail API.")
            self.service.users().settings().filters().delete(
                userId=self.user_id,
                id=filter_id
            ).execute()
            return True
        except Exception as e:
            raise Exception(f"Failed to delete filter: {str(e)}")

    # ------------------
    ## Message Stats
    # ------------------

    def get_unread_count(self) -> int:
        """
        Return the number of unread messages using the UNREAD system label.
        Leverages labels.get to read messagesUnread for the UNREAD label.
        """
        self._oauth_login()
        try:
            all_labels = self._list_labels()
            unread_label_id = [lid for lid in all_labels if lid['id'] == 'UNREAD'][0]

            log.info(f"Retrieving unread count from Gmail API.")
            label = self.service.users().labels().get(userId=self.user_id, id=unread_label_id).execute()
            return int(label.get('messagesUnread', 0))
        except Exception as e:
            raise Exception(f"Failed to retrieve unread count from Gmail: {e}")

    def get_total_count(self) -> int:
        """
        Return the total number of messages using the user profile endpoint.
        """
        self._oauth_login()
        try:
            log.info(f"Retrieving total message count from Gmail API.")
            profile = self.service.users().getProfile(userId=self.user_id).execute()
            return int(profile.get('messagesTotal', 0))
        except Exception as e:
            raise Exception(f"Failed to retrieve total message count from Gmail: {e}")

    # ---------------
    ## Gmail History
    # ---------------

    def list_history(self, history_types: list[str] = None) -> list[dict]:
        """
        Returns up to 500 history records since the last stored history id.
        - Keeps the latest history id in-memory (self._last_history_id).
        - If no history id is present, initializes it from users().getProfile().historyId
          and returns an empty list (no backfill on first call).
        - Does not paginate; assumes the full history fits in a single response (<= 500).

        Args:
            history_types: Optional list like ["labelAdded", "labelRemoved"].

        Returns:
            List of history record dicts.
        """
        if not history_types:
            history_types = []
        self._oauth_login()

        # Initialize the starting history id if not set; no backfill on first call
        if not self._last_history_id:
            try:
                log.info("Initializing Gmail history cursor.")
                profile = self.service.users().getProfile(userId=self.user_id).execute()
                self._last_history_id = profile.get("historyId")
            except Exception as e:
                raise Exception(f"Failed to initialize Gmail history cursor: {e}")
            log.warning(f"Initializing Gmail history cursor to {self._last_history_id}.")
            return []

        try:
            log.info(f"Retrieving Gmail history since {self._last_history_id} from Gmail API.")
            resp = self.service.users().history().list(
                userId=self.user_id,
                startHistoryId=self._last_history_id,
                historyTypes=history_types,
                maxResults=500,
            ).execute()
        except Exception as e:
            raise Exception(f"Failed to list Gmail history: {e}")

        # Update the in-memory cursor to the newest history id we can infer
        # Top-level historyId (point to last history included in the response)
        self._last_history_id = resp.get("historyId")
        log.info(f"Updated Gmail history cursor to {self._last_history_id}.")

        return resp.get("history", [])
