import os
import json
import logging
import asyncpg
from typing import Optional
from datetime import datetime

from coremind.state import CoreMindState
from langchain_core.messages import messages_to_dict, messages_from_dict

logger = logging.getLogger(__name__)


# -----------------------------
# Serialization Helpers
# -----------------------------
def _serialize_state(state: CoreMindState) -> dict:
    data = dict(state)

    if data.get("messages"):
        data["messages"] = messages_to_dict(data["messages"])

    if isinstance(data.get("called_tools"), set):
        data["called_tools"] = list(data["called_tools"])

    if isinstance(data.get("fetched_email_ids"), set):
        data["fetched_email_ids"] = list(data["fetched_email_ids"])

    return data


def _deserialize_state(data: dict) -> CoreMindState:
    if data.get("messages"):
        try:
            data["messages"] = messages_from_dict(data["messages"])
        except Exception as e:
            logger.error(f"Failed to deserialize messages: {e}")
            data["messages"] = []

    if isinstance(data.get("called_tools"), list):
        data["called_tools"] = set(data["called_tools"])

    if isinstance(data.get("fetched_email_ids"), list):
        data["fetched_email_ids"] = set(data["fetched_email_ids"])

    return CoreMindState(**data)


# -----------------------------
# Session Store (FIXED)
# -----------------------------
class SessionStore:
    def __init__(self):
        self.conn_str = os.getenv("SUPABASE_CONNECTION_STRING")
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Initialize connection pool (Vercel-safe)"""
        try:
            self.pool = await asyncpg.create_pool(
                self.conn_str,
                min_size=1,
                max_size=5,
                ssl="require",  # IMPORTANT for Supabase
            )
            logger.info("✅ Supabase connection pool initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize DB pool: {e}")

    # -----------------------------
    # Load Session
    # -----------------------------
    async def load_session(self, session_id: str) -> CoreMindState:
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT state FROM sessions WHERE chat_id = $1;",
                    session_id,
                )

                if row:
                    state_data = row["state"]

                    if isinstance(state_data, str):
                        state_data = json.loads(state_data)

                    return _deserialize_state(state_data)

        except Exception as e:
            logger.error(f"❌ Error loading session: {e}")

        return CoreMindState(messages=[])

    # -----------------------------
    # Save Session
    # -----------------------------
    async def save_session(self, session_id: str, state: CoreMindState):
        state_data = _serialize_state(state)

        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO sessions (chat_id, state, updated_at)
                    VALUES ($1, $2, now())
                    ON CONFLICT (chat_id)
                    DO UPDATE SET
                        state = EXCLUDED.state,
                        updated_at = EXCLUDED.updated_at;
                    """,
                    session_id,
                    json.dumps(state_data),
                )

        except Exception as e:
            logger.error(f"❌ Error saving session: {e}")