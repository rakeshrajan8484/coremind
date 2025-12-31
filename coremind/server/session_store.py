# coremind/server/session_store.py
from typing import Dict
from coremind.state import CoreMindState

_SESSIONS: Dict[str, CoreMindState] = {}

def get_session(session_id: str) -> CoreMindState:
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = CoreMindState(
            messages=[],
            objective=None,
            objective_queue=[],
        )
    return _SESSIONS[session_id]

def save_session(session_id: str, state: CoreMindState) -> None:
    _SESSIONS[session_id] = state
