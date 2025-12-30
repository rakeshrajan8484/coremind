# coremind/agents/nemesis/node.py

import json
from typing import Dict, Any
from coremind.agents.nemesis.agent import NemesisAgent
from coremind.objectives.registry import OBJECTIVE_REGISTRY
from coremind.logging import get_logger

log = get_logger("NEMESIS.NODE")


def make_nemesis_node():
    """
    NEMESIS = pure execution node.

    Responsibilities:
    - Execute exactly ONE objective
    - NEVER plan
    - NEVER resolve semantics
    - NEVER decide if IRIS should run
    - Always return control to ATLAS
    """

    agent = NemesisAgent()

    def nemesis_node(state: Dict[str, Any]) -> Dict[str, Any]:
        log.info("Entered NEMESIS node")

        objective = state.get("objective")

        log.warning(
            "NEMESIS RECEIVED OBJECTIVE:\n%s",
            json.dumps(objective, indent=2) if objective else "<NONE>"
        )

        # --------------------------------------------------
        # 1️⃣ No objective → nothing to execute
        # --------------------------------------------------
        if not objective:
            return {
                **state,
                "current_agent": "atlas",
            }

        # --------------------------------------------------
        # 2️⃣ Resolve ObjectiveSpec (authoritative)
        # --------------------------------------------------
        key = (objective.get("domain"), objective.get("intent"))
        spec = OBJECTIVE_REGISTRY.get(key)

        if not spec:
            log.error("NEMESIS RECEIVED UNKNOWN OBJECTIVE: %s", key)
            return {
                **state,
                "result": {
                    "status": "error",
                    "summary": "Unknown objective",
                    "artifacts": {},
                },
                "objective": None,
                "current_agent": "atlas",
            }

        # --------------------------------------------------
        # 3️⃣ Identity requirement (SPEC-DRIVEN ONLY)
        # --------------------------------------------------
        resolved_id = state.get("resolved_id")

        if spec.requires_concrete_identity and not resolved_id:
            log.warning(
                "NEMESIS DEFERRING: objective requires concrete identity "
                "but no resolved_id present.\nObjective=%s",
                json.dumps(objective, indent=2),
            )

            return {
                **state,
                "objective": None,
                "needs_reference_resolution": True,
                "reference": json.dumps(objective.get("target", {}).get("filter", {})),
                "current_agent": "atlas",
            }

        # --------------------------------------------------
        # 4️⃣ Execute objective (NO MODIFICATION)
        # --------------------------------------------------
        try:
            result = agent.run(state)
        except Exception as e:
            log.exception("NEMESIS EXECUTION FAILED")

            return {
                **state,
                "result": {
                    "status": "error",
                    "summary": str(e),
                    "artifacts": {},
                },
                "objective": None,
                "current_agent": "atlas",
            }

        # --------------------------------------------------
        # 5️⃣ Return control to ATLAS
        # --------------------------------------------------
        return {
            **state,
            "result": result,
            "objective": None,   # 🔒 objective is single-use
            "current_agent": "atlas",
        }

    return nemesis_node
