import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from typing import Dict, Any
from coremind.storage.session_store import SessionStore
from coremind.state import CoreMindState
from langchain_core.messages import HumanMessage

async def main():
    store = SessionStore()
    await store.initialize()
    
    # Check if table exists, else pass. (assuming table is created as user said)
    state = CoreMindState(
        messages=[HumanMessage(content="Hello world!")],
        called_tools={"tool1", "tool2"},
        fetched_email_ids=set()
    )
    
    # Save
    print("Saving...")
    await store.save_session("test_chat_id_123", state)
    print("Saved.")
    
    # Load
    print("Loading...")
    loaded = await store.load_session("test_chat_id_123")
    print(f"Loaded called_tools: {loaded.get('called_tools')}")
    print(f"Loaded messages: {loaded.get('messages')}")

if __name__ == "__main__":
    asyncio.run(main())
