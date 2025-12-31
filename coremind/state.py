from typing import Any, Dict, List, Literal, Optional, Set, TypedDict

class CoreMindState(TypedDict, total=False):
    """
    CoreMind global state contract.
    This is the ONLY shared state shape allowed across ATLAS, IRIS, and NEMESIS.
    """

    # =========================
    # Routing (LangGraph)
    # =========================
    current_agent: Literal["atlas", "nemesis", "iris"]

    # =========================
    # User / Intent
    # =========================
    intent: str
    messages: List[Any]

    # =========================
    # Planning / Orchestration (ATLAS)
    # =========================
    objective: Optional[Dict[str, Any]]
    objective_queue: List[Dict[str, Any]]

    # =========================
    # Discovery / Resolution
    # =========================
    candidates: List[Dict[str, Any]]
    reference: Optional[str]
    needs_reference_resolution: bool
    resolved_id: Optional[str]

    # =========================
    # 🔒 Email Draft Lifecycle (NEW)
    # =========================
    last_draft_id: Optional[str]

    # =========================
    # Execution (NEMESIS)
    # =========================
    observations: List[Dict[str, Any]]
    called_tools: Set[str]
    fetched_email_ids: Set[str]
    force_done: bool

    # =========================
    # Result / Termination
    # =========================
    result: Optional[Dict[str, Any]]
    terminated: bool
