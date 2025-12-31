from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from coremind.graph.graph import build_graph
from coremind.state import CoreMindState

app = FastAPI()
graph = build_graph()

# 🔒 In-memory session store (OK for now)
SESSIONS: dict[str, CoreMindState] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # -------------------------------------------------
    # Load or create session
    # -------------------------------------------------
    if req.session_id in SESSIONS:
        state = SESSIONS[req.session_id]
        state["messages"].append(HumanMessage(content=req.message))
    else:
        state = CoreMindState(
            messages=[HumanMessage(content=req.message)]
        )

    # -------------------------------------------------
    # Run LangGraph
    # -------------------------------------------------
    new_state = graph.invoke(state)

    # -------------------------------------------------
    # Persist updated state
    # -------------------------------------------------
    SESSIONS[req.session_id] = new_state

    # -------------------------------------------------
    # Extract assistant reply
    # -------------------------------------------------
    messages = new_state.get("messages", [])
    reply = messages[-1].content if messages else ""

    return ChatResponse(
        reply=reply,
        session_id=req.session_id,
    )
