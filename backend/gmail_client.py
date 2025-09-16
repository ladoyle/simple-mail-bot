from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import keyring
import json
import os
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

    user_id = 'me'

    # If modifying these scopes, delete the file token.pickle.
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.labels',  # For creating/modifying labels
        'https://www.googleapis.com/auth/gmail.modify',  # For modifying emails (applying labels)
        'https://www.googleapis.com/auth/gmail.settings.basic'  # Required for filter management
    ]

    # Get redirect_uri based on the environment
    redirect_uri = 'https://my-frontend-domain.com/'\
        if 'MAIL_BOT_TO_GMAIL' in os.environ else 'http://localhost:5000/oauth/callback'

    def __init__(self):
        pass

    def get_authorization_url(self):
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri
        )
        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline', include_granted_scopes='true')
        return auth_url

    def exchange_code_for_token(self, code):
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json',
            scopes=self.SCOPES,
            redirect_uri=self.redirect_uri
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        profile = self.get_user_profile_from_creds(creds)
        # Store tokens in keyring using email as key
        user_email = profile.get("emailAddress")
        keyring.set_password('gmail_api', user_email, creds.to_json())
        return user_email, profile.get("historyId"), creds.token

    def remove_user(self, email, access_token):
        """
        Remove user by deleting their OAuth tokens from keyring.
        """
        # Retrieve tokens from keyring
        self.validate_gmail_access(email, access_token)

        # Revoke creds
        log.warning(f"Removing Gmail API tokens for user {email}.")
        import requests
        revoke_url = "https://oauth2.googleapis.com/revoke"
        response = requests.post(revoke_url, params={'token': access_token})
        if response.status_code != 200:
            log.error(f"Failed to revoke token for {email}: {response.text}")
        keyring.delete_password('gmail_api', email)

    def get_user_profile_from_creds(self, creds):
        return self._get_user_profile(creds.token)

    def _get_user_profile(self, access_token):
        # Build a temporary credentials object to get the email
        creds = Credentials(token=access_token, scopes=self.SCOPES)
        service = build('gmail', 'v1', credentials=creds)
        return service.users().getProfile(userId=self.user_id).execute()

    def validate_gmail_access(self, email, access_token):
        # Retrieve tokens from keyring
        creds = self._get_creds_from_email(email)
        # Validate creds with token
        if access_token != creds.token:
            raise Exception(f"Invalid access token for {email}")
        return creds

    def get_api_client(self, email, access_token):
        creds = self.validate_gmail_access(email, access_token)
        # Refresh if needed
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed tokens
            keyring.set_password('gmail_api', email, creds.to_json())
        return build('gmail', 'v1', credentials=creds, discoveryServiceUrl="https://gmail.googleapis.com/$discovery/rest?version=v1")

    def _get_creds_from_email(self, email):
        stored_creds = keyring.get_password('gmail_api', email)
        if not stored_creds:
            raise Exception(f"No OAuth tokens found for {email}")
        return Credentials.from_authorized_user_info(json.loads(stored_creds), self.SCOPES)

    # -------------
    ## Labels
    # -------------

    def _list_labels(self, user_email: str, access_token: str) -> list[dict]:
        """Lists all labels in the user's account."""
        log.info("Retrieving labels from Gmail API.")
        try:
            results = self.get_api_client(user_email, access_token).users().labels().list(userId=self.user_id).execute()
        except Exception as e:
            raise Exception(f"Failed to list labels: {e}")
        log.info(f"Retrieved {len(results.get('labels', []))} labels from Gmail.")
        return results.get('labels', [])

    def list_labels(self, user_email: str, access_token: str) -> list[dict]:
        """Lists all labels in the user's account."""
        return self._list_labels(user_email, access_token)

    def create_label(self, user_email: str, access_token: str, name: str, text_color: str, bg_color: str) -> dict:
        """Creates a new label."""
        try:
            label_object = {
                'name': name,
                'messageListVisibility': 'show',
                'labelListVisibility': 'labelShow',
                'color': {
                    "textColor": text_color,
                    "backgroundColor": bg_color
                }
            }

            log.info(f"Creating label '{name}' in Gmail API.")
            created_label = self.get_api_client(user_email, access_token).users().labels().create(
                userId=self.user_id,
                body=label_object
            ).execute()

            return created_label
        except Exception as e:
            raise Exception(f"Failed to create label: {e}")

    def delete_label(self, label_id: str, user_email: str, access_token: str) -> bool:
        """Deletes a label by its ID."""
        try:
            log.warning(f"Deleting label '{label_id}' from Gmail API.")
            self.get_api_client(user_email, access_token).users().labels().delete(
                userId=self.user_id,
                id=label_id
            ).execute()
            return True
        except Exception as e:
            raise Exception(f"Failed to delete label: {str(e)}")

    # --------------
    ## Filters
    # --------------

    def create_filter(self, criteria: dict, actions: dict, user_email: str, access_token: str) -> dict:
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
            user_email (str): Gmail address to create the filter for
            access_token (str): Valid OAuth access token
        """
        try:
            filter_object = {
                'criteria': criteria,
                'action': actions
            }

            log.info(f"Creating filter in Gmail API.")
            result = self.get_api_client(user_email, access_token).users().settings().filters().create(
                userId=self.user_id,
                body=filter_object
            ).execute()
            return result
        except Exception as e:
            raise Exception(f"Failed to create filter: {str(e)}")

    def list_filters(self, user_email: str, access_token: str) -> list[dict]:
        """List all filters in the Gmail account."""
        try:
            log.info(f"Listing filters in Gmail API.")
            results = self.get_api_client(user_email, access_token).users().settings().filters().list(
                userId=self.user_id
            ).execute()
            log.info(f"Retrieved {len(results.get('filter', []))} filters from Gmail.")
            return results.get('filter', [])
        except Exception as e:
            raise Exception(f"Failed to list filters: {str(e)}")

    def delete_filter(self, filter_id: str, user_email: str, access_token: str) -> bool:
        """Delete a specific filter by ID."""
        try:
            log.warning(f"Deleting filter '{filter_id}' from Gmail API.")
            self.get_api_client(user_email, access_token).users().settings().filters().delete(
                userId=self.user_id,
                id=filter_id
            ).execute()
            return True
        except Exception as e:
            raise Exception(f"Failed to delete filter: {str(e)}")

    # ------------------
    ## Message Stats
    # ------------------

    def get_unread_count(self, user_email: str, access_token: str) -> int:
        """
        Return the number of unread messages using the UNREAD system label.
        Leverages labels.get to read messagesUnread for the UNREAD label.
        """
        
        all_labels = self._list_labels(user_email, access_token)
        unread_label_id = [lid for lid in all_labels if lid['id'] == 'UNREAD'][0]

        try:
            log.info(f"Retrieving unread count from Gmail API.")
            label = self.get_api_client(user_email, access_token).users().labels().get(
                userId=self.user_id,
                id=unread_label_id['id']
            ).execute()
            return int(label.get('messagesUnread', 0))
        except Exception as e:
            raise Exception(f"Failed to retrieve unread count from Gmail: {e}")

    def get_total_count(self, user_email: str, access_token: str) -> int:
        """
        Return the total number of messages using the user profile endpoint.
        """
        try:
            log.info(f"Retrieving total message count from Gmail API.")
            profile = self.get_api_client(user_email, access_token).users().getProfile(userId=self.user_id).execute()
            return int(profile.get('messagesTotal', 0))
        except Exception as e:
            raise Exception(f"Failed to retrieve total message count from Gmail: {e}")

    # ---------------
    ## Gmail History
    # ---------------

    def list_history(self, user_email: str, history_id: str, history_types: list[str] = None) -> tuple[str, list[dict]]:
        """
        Returns up to 500 history records since the last stored history id.
        - Keeps the latest history id in-memory (self._last_history_id).
        - If no history id is present, initializes it from users().getProfile().historyId
          and returns an empty list (no backfill on first call).
        - Does not paginate; assumes the full history fits in a single response (<= 500).

        Args:
            :param user_email: gmail address to retrieve history
            :param history_id: id of the last retrieved history record
            :param history_types: Optional list like ["labelAdded", "labelRemoved"]

        Returns:
            List of history record dicts.
        """
        if history_types is None:
            history_types = []

        creds = self._get_creds_from_email(user_email)
        # Refresh if needed
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save refreshed tokens
            keyring.set_password('gmail_api', user_email, creds.to_json())
        gmail_api = build('gmail', 'v1', credentials=creds, discoveryServiceUrl="https://gmail.googleapis.com/$discovery/rest?version=v1")

        try:
            log.info(f"Retrieving Gmail history since {history_id} from Gmail API.")
            resp = gmail_api.users().history().list(
                userId=self.user_id,
                startHistoryId=history_id,
                historyTypes=history_types,
                maxResults=500,
            ).execute()
        except Exception as e:
            raise Exception(f"Failed to list Gmail history: {e}")

        # Update the in-memory cursor to the newest history id we can infer
        # Top-level historyId (point to last history included in the response)
        updated_history_id = resp.get("historyId")
        log.info(f"Updated Gmail history cursor to {updated_history_id}.")

        return updated_history_id, resp.get("history", [])
