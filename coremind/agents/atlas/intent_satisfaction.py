from typing import Literal, Dict, Any


ISCState = Literal[
    "SATISFIED",
    "INCOMPLETE",
    "AMBIGUOUS",
    "FAILED",
]


def evaluate_intent_satisfaction(
    *,
    intent: str,
    result: Dict[str, Any] | None,
) -> ISCState:
    """
    Pure Intent Satisfaction Contract (ISC) evaluator.

    Inputs:
    - intent: semantic user intent (string)
    - result: NEMESIS execution result (or None)

    Output:
    - One of: SATISFIED | INCOMPLETE | AMBIGUOUS | FAILED

    Guarantees:
    - Deterministic
    - Domain-agnostic
    - No tool awareness
    - No execution reasoning
    """

    if not intent or not result:
        return "FAILED"

    if result.get("status") != "success":
        return "FAILED"

    artifacts = result.get("artifacts", {})
    raw_data = artifacts.get("raw_data")
    candidates = artifacts.get("candidates", [])

    intent_lc = intent.lower()

    # ─────────────────────────────────────────────
    # 1️⃣ Ambiguity / incompleteness
    # ─────────────────────────────────────────────
    if isinstance(candidates, list) and len(candidates) > 1:
        if any(
            k in intent_lc
            for k in (
                "summarize",
                "summary",
                "explain",
                "details",
                "describe",
                "analyze",
            )
        ):
            return "INCOMPLETE"
        return "AMBIGUOUS"

    # ─────────────────────────────────────────────
    # 2️⃣ Depth requirement
    # ─────────────────────────────────────────────
    needs_depth = any(
        k in intent_lc
        for k in (
            "summarize",
            "summary",
            "explain",
            "details",
            "describe",
            "analyze",
        )
    )

    if needs_depth:
        if raw_data is None:
            return "INCOMPLETE"

        if isinstance(raw_data, list):
            return "INCOMPLETE"

        if isinstance(raw_data, dict):
            content_keys = {
                "content",
                "body",
                "text",
                "full",
                "details",
                "message",
            }
            if not any(k in raw_data for k in content_keys):
                return "INCOMPLETE"

    # ─────────────────────────────────────────────
    # 3️⃣ Specific reference expectation
    # ─────────────────────────────────────────────
    if "the " in intent_lc and raw_data is None:
        return "INCOMPLETE"

    return "SATISFIED"
