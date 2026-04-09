import os
import json
from functools import lru_cache

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


@lru_cache(maxsize=1)
def get_gmail_service():
    """
    Gmail client using OAuth 2.0 User Credentials.
    - Prompts user in browser on first run.
    - Saves and refreshes tokens locally to gmail_token.json.
    """
    creds = None
    token_path = "gmail_token.json"
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Token refresh failed: {e}")
                creds = None

        if creds is None:
            credential_json = os.environ.get("GMAIL_CREDENTIAL_JSON")
            if not credential_json:
                raise RuntimeError("Missing GMAIL_CREDENTIAL_JSON in environment")
            
            try:
                client_config = json.loads(credential_json)
            except json.JSONDecodeError:
                raise RuntimeError("Invalid JSON in GMAIL_CREDENTIAL_JSON")
                
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            # This opens the browser for authorization
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())

    return build(
        "gmail",
        "v1",
        credentials=creds,
        cache_discovery=False,
    )