import os
import json
import logging
import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime

from coremind.state import CoreMindState
from langchain_core.messages import messages_to_dict, messages_from_dict

logger = logging.getLogger(__name__)

def _serialize_state(state: CoreMindState) -> dict:
    data = dict(state)
    if data.get("messages"):
        data["messages"] = messages_to_dict(data["messages"])
    if "called_tools" in data and isinstance(data["called_tools"], set):
        data["called_tools"] = list(data["called_tools"])
    if "fetched_email_ids" in data and isinstance(data["fetched_email_ids"], set):
        data["fetched_email_ids"] = list(data["fetched_email_ids"])
    return data

def _deserialize_state(data: dict) -> CoreMindState:
    if data.get("messages"):
        try:
            data["messages"] = messages_from_dict(data["messages"])
        except Exception as e:
            logger.error(f"Failed to deserialize messages: {e}")
            data["messages"] = []
    if "called_tools" in data and isinstance(data["called_tools"], list):
        data["called_tools"] = set(data["called_tools"])
    if "fetched_email_ids" in data and isinstance(data["fetched_email_ids"], list):
        data["fetched_email_ids"] = set(data["fetched_email_ids"])
    return CoreMindState(**data)


class SessionStore:
    def __init__(self):
        self.conn_str = os.getenv("SUPABASE_CONNECTION_STRING")

    async def initialize(self):
        """Verify DB connection."""
        try:
            conn = await asyncpg.connect(self.conn_str)
            await conn.execute("SELECT 1;")
            await conn.close()
            logger.info("Supabase DB async connection initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")

    async def load_session(self, session_id: str) -> CoreMindState:
        """Loads session state from Supabase or returns a new empty state."""
        try:
            conn = await asyncpg.connect(self.conn_str)
            row = await conn.fetchrow("SELECT state FROM sessions WHERE chat_id = $1;", session_id)
            await conn.close()
            
            if row:
                state_data = row['state']
                if isinstance(state_data, str):
                    state_data = json.loads(state_data)
                return _deserialize_state(state_data)
        except Exception as e:
            logger.error(f"Error loading session from Supabase using asyncpg: {e}")
        
        # Default empty state
        return CoreMindState(messages=[])

    async def save_session(self, session_id: str, state: CoreMindState):
        """Saves session state to Supabase."""
        state_data = _serialize_state(state)
        now = datetime.now()
        
        try:
            conn = await asyncpg.connect(self.conn_str)
            await conn.execute(
                """
                INSERT INTO sessions (chat_id, state, updated_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (chat_id) DO UPDATE SET
                    state = EXCLUDED.state,
                    updated_at = EXCLUDED.updated_at;
                """,
                session_id, json.dumps(state_data), now
            )
            await conn.close()
        except Exception as e:
            logger.error(f"Error saving session to Supabase using asyncpg: {e}")
