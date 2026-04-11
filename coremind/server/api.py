from fastapi import FastAPI, Request
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from coremind.graph.graph import build_graph
from coremind.state import CoreMindState
from coremind.storage.session_store import SessionStore
from typing import Optional, Dict, Any

import asyncio
import os
import logging
import requests
from dotenv import load_dotenv
load_dotenv()
# -------------------------------------------------
# App + Graph Init
# -------------------------------------------------

app = FastAPI()

graph = build_graph()
SESSION_STORE = SessionStore()

logger = logging.getLogger(__name__)

# -------------------------------------------------
# Health Check
# -------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}

# -------------------------------------------------
# Telegram Config
# -------------------------------------------------

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# -------------------------------------------------
# Models
# -------------------------------------------------

class ChatRequest(BaseModel):
    session_id: str
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


# -------------------------------------------------
# Core Chat Endpoint (Internal / API)
# -------------------------------------------------

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):

    try:
        
        # ✅ Extract root_path safely
        root_path = req.context.get("root_path") if req.context else None
        
        # ✅ Load session
        state = await SESSION_STORE.load_session(req.session_id)
        if root_path:
            state["root_path"] = root_path
        if not state:
            state = {
                "messages": [],
                "objective": None,
                "objective_queue": [],
                "completed_objectives": [],
            }

        # ✅ CRITICAL FIX — reset execution state
        state["objective"] = None
        state["objective_queue"] = []
        state["result"] = None
        state["terminated"] = False
       
        # ✅ Append user message
        state["messages"].append(HumanMessage(content=req.message))

        # ✅ Run graph
        new_state = await asyncio.to_thread(graph.invoke, state)

        # ✅ Persist root_path (optional but recommended)
        new_state["root_path"] = root_path
        print("new_state", new_state)
        # ✅ Save session
        await SESSION_STORE.save_session(req.session_id, new_state)
        
        # ✅ Extract reply
        messages = new_state.get("messages", [])
        reply = messages[-1].content if messages else ""

        return ChatResponse(
            reply=reply,
            session_id=req.session_id
        )

    except Exception as e:
        logger.exception("🔥 Chat API failed")

        return ChatResponse(
            reply=f"Error: {str(e)}",
            session_id=req.session_id,
        )

# -------------------------------------------------
# Telegram Webhook Endpoint
# -------------------------------------------------
@app.post("/api/telegram")
@app.post("/telegram")
async def telegram_webhook(request: Request):

    # -----------------------------
    # Parse request safely
    # -----------------------------
    try:
        data = await request.json()
    except Exception:
        return {"ok": True}

    logger.info(f"Incoming Telegram update: {data}")

    if not data or "message" not in data:
        return {"ok": True}

    chat_id = str(data["message"]["chat"]["id"])
    user_text = data["message"].get("text", "")

    if not user_text:
        return {"ok": True}

    # -----------------------------
    # ✅ Get session store (lazy init)
    # -----------------------------
    try:
        store = await request.app.state.get_session_store()
    except Exception as e:
        logger.error(f"❌ Session store init failed: {e}")
        store = None

    # -----------------------------
    # Load session (safe fallback)
    # -----------------------------
    try:
        state = await store.load_session(chat_id) if store else None
    except Exception as e:
        logger.error(f"❌ Load session failed: {e}")
        state = None

    if not state:
        state = {
            "messages": [],
            "objective": None,
            "objective_queue": [],
            "completed_objectives": [],
        }

    # -----------------------------
    # Reset execution state
    # -----------------------------
    state["objective"] = None
    state["objective_queue"] = []
    state["result"] = None
    state["terminated"] = False

    # -----------------------------
    # Add user message
    # -----------------------------
    state["messages"].append(HumanMessage(content=user_text))

    # -----------------------------
    # Run graph safely
    # -----------------------------
    try:
        new_state = await asyncio.to_thread(graph.invoke, state)
    except Exception:
        logger.exception("🔥 Telegram Webhook Graph execution failed")
        return {"ok": True}  # prevent Telegram retry loop

    # -----------------------------
    # Save session (non-blocking safe)
    # -----------------------------
    if store:
        try:
            await store.save_session(chat_id, new_state)
        except Exception as e:
            logger.error(f"❌ Save session failed: {e}")

    # -----------------------------
    # Extract reply
    # -----------------------------
    messages = new_state.get("messages", [])
    reply = messages[-1].content if messages else "..."

    # -----------------------------
    # Send reply to Telegram (safe)
    # -----------------------------
    try:
        requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": reply,
            },
            timeout=5,  # prevent hanging
        )
    except Exception as e:
        logger.error(f"❌ Telegram send failed: {e}")

    return {"ok": True}


@app.get("/")
async def root():
    return {"status": "running"}