import aiosqlite
import pickle
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from coremind.state import CoreMindState
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

DB_PATH = "coremind.db"

class SessionStore:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    async def initialize(self):
        """Creates the sessions table if it doesn't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    state_data BLOB,
                    updated_at TIMESTAMP
                )
            """)
            await db.commit()

    async def load_session(self, session_id: str) -> CoreMindState:
        """Loads session state or returns a new empty state."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT state_data FROM sessions WHERE session_id = ?", (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                
                if row:
                    try:
                        return pickle.loads(row[0])
                    except Exception as e:
                        logger.error(f"Failed to deserialize session {session_id}: {e}")
                        # Fallback to empty state? Or re-raise?
                        # For robustness, start fresh if corrupted.
                        pass
        
        # Default empty state
        return CoreMindState(messages=[])

    async def save_session(self, session_id: str, state: CoreMindState):
        """Saves session state."""
        data = pickle.dumps(state)
        now = datetime.now()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO sessions (session_id, state_data, updated_at)
                VALUES (?, ?, ?)
                """,
                (session_id, data, now),
            )
            await db.commit()
