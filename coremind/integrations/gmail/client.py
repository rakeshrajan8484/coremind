import os
import json
from functools import lru_cache
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from supabase import create_client

# -------------------------
# CONFIG
# -------------------------
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

SUPABASE_URL = os.environ["SUPABASE_PROJECT_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# -------------------------
# DB HELPERS
# -------------------------
def get_token_from_db(user_id='user_id'):
    response = (
        supabase.table("gmail_tokens")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )

    if response.data and len(response.data) > 0:
        return response.data[0]

    return None


def save_or_update_token(user_id: str, creds: Credentials):
    token_data = json.loads(creds.to_json())

    payload = {
        "user_id": user_id,
        "access_token": token_data.get("token"),
        "refresh_token": token_data.get("refresh_token"),
        "token_uri": token_data.get("token_uri"),
        "client_id": token_data.get("client_id"),
        "client_secret": token_data.get("client_secret"),
        "scopes": token_data.get("scopes"),
        "expiry": token_data.get("expiry"),
        "updated_at": datetime.utcnow().isoformat(),
    }

    # ⚠️ Preserve refresh_token if Google doesn't send it again
    existing = get_token_from_db(user_id)
    if existing and not payload["refresh_token"]:
        payload["refresh_token"] = existing.get("refresh_token")

    supabase.table("gmail_tokens").upsert(payload).execute()


# -------------------------
# MAIN CLIENT
# -------------------------
def get_gmail_service(user_id: str):
    """
    Gmail client using Supabase-backed OAuth storage.
    """

    creds = None
    token_row = get_token_from_db(user_id)

    # -------------------------
    # LOAD EXISTING TOKEN
    # -------------------------
    if token_row:
        creds_dict = {
            "token": token_row["access_token"],
            "refresh_token": token_row["refresh_token"],
            "token_uri": token_row["token_uri"],
            "client_id": token_row["client_id"],
            "client_secret": token_row["client_secret"],
            "scopes": token_row["scopes"],
        }

        creds = Credentials.from_authorized_user_info(creds_dict, SCOPES)

    # -------------------------
    # REFRESH TOKEN IF NEEDED
    # -------------------------
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_or_update_token(user_id, creds)
        except Exception as e:
            print(f"Token refresh failed: {e}")
            creds = None

    # -------------------------
    # FIRST-TIME LOGIN
    # -------------------------
    if not creds or not creds.valid:
        credential_json = os.environ.get("GMAIL_CREDENTIAL_JSON")
        if not credential_json:
            raise RuntimeError("Missing GMAIL_CREDENTIAL_JSON")

        client_config = json.loads(credential_json)

        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

        # ⚠️ For production, replace this with redirect-based OAuth
        creds = flow.run_local_server(port=0)

        save_or_update_token(user_id, creds)

    # -------------------------
    # BUILD SERVICE
    # -------------------------
    return build(
        "gmail",
        "v1",
        credentials=creds,
        cache_discovery=False,
    )