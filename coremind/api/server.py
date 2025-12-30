# coremind/api/server.py

from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from coremind.graph.graph import build_graph
from coremind.state import CoreMindState

app = FastAPI(title="CoreMind API")

# Build graph ONCE at startup
graph_app = build_graph()


# -----------------------------
# Request / Response models
# -----------------------------

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    full_state: dict | None = None


# -----------------------------
# POST /chat
# -----------------------------

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Accepts user input and returns assistant response.
    """

    initial_state = CoreMindState(
        messages=[
            HumanMessage(content=req.message)
        ]
    )

    final_state = graph_app.invoke(initial_state)

    messages = final_state.get("messages", [])
    assistant_reply = (
        messages[-1].content if messages else "No response generated."
    )

    return ChatResponse(
        response=assistant_reply,
        full_state=final_state,  # keep for debugging; remove in prod if needed
    )
