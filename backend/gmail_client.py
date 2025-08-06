def get_gmail_client():
    global gmail_client
    if gmail_client is None:
        gmail_client = GmailClient()
    return gmail_client

class GmailClient:
    pass