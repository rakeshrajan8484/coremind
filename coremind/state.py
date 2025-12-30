from typing import TypedDict, Optional, Dict, Any, List, Set


class CoreMindState(TypedDict, total=False):
    """
    CoreMind global state contract.
    This is the ONLY shared state shape allowed across ATLAS, IRIS, and NEMESIS.
    """

    # =========================
    # User / Intent layer
    # =========================
    intent: str                      # Raw or normalized user intent

    # =========================
    # Planning layer (ATLAS)
    # =========================
    plan: List[Dict[str, Any]]        # High-level steps decided by ATLAS (optional)
    current_step: Optional[int]

    # =========================
    # Execution layer (NEMESIS)
    # =========================
    objective: Dict[str, Any]         # Single executable objective (REQUIRED for NEMESIS)
    observations: List[Dict[str, Any]]
    called_tools: Set[str]
    fetched_email_ids: Set[str]
    force_done: bool

    # =========================
    # Resolution layer (IRIS)
    # =========================
    unresolved_references: List[str]
    resolved_references: Dict[str, Any]

    # =========================
    # Final output
    # =========================
    result: Dict[str, Any]
    terminated: bool
