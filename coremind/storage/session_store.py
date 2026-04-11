import psycopg2
import os
import json
import asyncio
import logging
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

    def _get_connection(self):
        return psycopg2.connect(self.conn_str)

    async def initialize(self):
        """Verify DB connection."""
        def _init():
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1;")
                logger.info("Supabase DB connection initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {e}")
        await asyncio.to_thread(_init)

    async def load_session(self, session_id: str) -> CoreMindState:
        """Loads session state from Supabase or returns a new empty state."""
        def _load():
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT state FROM sessions WHERE chat_id = %s;", (session_id,))
                        row = cur.fetchone()
                        if row:
                            # row[0] is dict if psycopg2 parses JSON automatically, else string
                            state_data = row[0]
                            if isinstance(state_data, str):
                                state_data = json.loads(state_data)
                            return _deserialize_state(state_data)
            except psycopg2.Error as e:
                logger.error(f"Error loading session from Supabase: {e}")
            
            # Default empty state
            return CoreMindState(messages=[])
            
        return await asyncio.to_thread(_load)

    async def save_session(self, session_id: str, state: CoreMindState):
        """Saves session state to Supabase."""
        def _save():
            state_data = _serialize_state(state)
            now = datetime.now()
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO sessions (chat_id, state, updated_at)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (chat_id) DO UPDATE SET
                                state = EXCLUDED.state,
                                updated_at = EXCLUDED.updated_at;
                            """,
                            (session_id, json.dumps(state_data), now)
                        )
                    conn.commit()
            except psycopg2.Error as e:
                logger.error(f"Error saving session to Supabase: {e}")

        await asyncio.to_thread(_save)
