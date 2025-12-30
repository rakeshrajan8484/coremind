from pathlib import Path
import pickle

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

COREMIND_DIR = Path.home() / ".coremind"
TOKEN_PATH = COREMIND_DIR / "gmail_token.pkl"
CREDS_PATH = COREMIND_DIR / "gmail_credentials.json"


def get_gmail_service():
    """
    Infrastructure function.
    Handles OAuth and returns an authenticated Gmail service client.
    """

    creds = None

    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, "rb") as token:
            creds = pickle.load(token)

        # 🔒 Invalidate token if required scopes are missing
        if not creds.scopes or not set(SCOPES).issubset(set(creds.scopes)):
            creds = None


    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # ⚠️ Refresh will NOT upgrade scopes
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDS_PATH,
                SCOPES,
            )
            print("[GMAIL] Waiting for OAuth consent in browser...")
            creds = flow.run_local_server(
                port=0,
                open_browser=True,
                prompt="consent",
                include_granted_scopes=False,  # 🔒 CRITICAL
            )

        COREMIND_DIR.mkdir(exist_ok=True)
        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)

    # 🔒 HARD SAFETY CHECK
    if "https://www.googleapis.com/auth/gmail.modify" not in creds.scopes:
        raise RuntimeError(
            f"Gmail modify scope NOT granted. Actual scopes: {creds.scopes}"
        )

    return build("gmail", "v1", credentials=creds)
