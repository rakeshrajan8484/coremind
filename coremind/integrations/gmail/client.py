from pathlib import Path
import pickle
import json
import os
import tempfile

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

COREMIND_DIR = Path.home() / ".coremind"
TOKEN_PATH = COREMIND_DIR / "gmail_token.pkl"


def _get_creds_file_from_env():
    """
    Reads Gmail credentials JSON from environment variable
    and writes it to a temporary file (required by Google lib).
    """
    creds_json = os.environ.get("GMAIL_CREDENTIALS_JSON")

    if not creds_json:
        return None

    data = json.loads(creds_json)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    with open(tmp.name, "w") as f:
        json.dump(data, f)

    return tmp.name


def get_gmail_service():
    """
    Infrastructure function.
    Handles OAuth and returns an authenticated Gmail service client.
    """

    creds = None

    # --------------------------------------------------
    # 🔒 Load existing token
    # --------------------------------------------------
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, "rb") as token:
            creds = pickle.load(token)

        if not creds.scopes or not set(SCOPES).issubset(set(creds.scopes)):
            creds = None

    # --------------------------------------------------
    # 🔒 Ensure valid credentials
    # --------------------------------------------------
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                creds = None

        if not creds:
            creds_file = _get_creds_file_from_env()

            if not creds_file:
                raise RuntimeError(
                    "GMAIL_CREDENTIALS_JSON not set in environment"
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                creds_file,
                SCOPES,
            )

            print("[GMAIL] Waiting for OAuth consent...")

            creds = flow.run_local_server(
                port=0,
                open_browser=False,  # 🔥 IMPORTANT for serverless
                prompt="consent",
                include_granted_scopes=False,
            )

        COREMIND_DIR.mkdir(exist_ok=True)
        with open(TOKEN_PATH, "wb") as token:
            pickle.dump(creds, token)

    # --------------------------------------------------
    # 🔒 HARD SAFETY CHECK
    # --------------------------------------------------
    if "https://www.googleapis.com/auth/gmail.modify" not in creds.scopes:
        raise RuntimeError(
            f"Gmail modify scope NOT granted. Actual scopes: {creds.scopes}"
        )

    return build("gmail", "v1", credentials=creds)