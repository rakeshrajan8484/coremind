import json
from typing import Dict, Any

from coremind.agents.nemesis.agent import NemesisAgent
from coremind.objectives.registry import OBJECTIVE_REGISTRY
from coremind.logging import get_logger

log = get_logger("NEMESIS.NODE")


def has_concrete_identity(objective: Dict[str, Any], state: Dict[str, Any]) -> bool:
    if state.get("resolved_id"):
        return True

    target = objective.get("target") or {}
    filter_ = target.get("filter") or {}
    entity = target.get("entity")

    if entity == "draft" and filter_.get("draft_id"):
        return True

    if entity == "message" and filter_.get("id"):
        return True

    if entity == "thread" and filter_.get("thread_id"):
        return True

    return False


def make_nemesis_node():
    """
    NEMESIS = pure execution node.

    Responsibilities:
    - Execute exactly ONE objective
    - NEVER plan
    - NEVER resolve semantics
    - TRUST concrete objectives from ATLAS
    """

    agent = NemesisAgent()

    def nemesis_node(state: Dict[str, Any]) -> Dict[str, Any]:
        log.info("Entered NEMESIS node")

        objective = state.get("objective")

        log.warning(
            "NEMESIS RECEIVED OBJECTIVE:\n%s",
            json.dumps(objective, indent=2) if objective else "<NONE>"
        )

        if not objective:
            return {
                **state,
                "current_agent": "atlas",
            }

        objective_id = objective.get("_objective_id")

        # --------------------------------------------------
        # Resolve ObjectiveSpec
        # --------------------------------------------------
        key = (objective.get("domain"), objective.get("intent"))
        spec = OBJECTIVE_REGISTRY.get(key)

        if not spec:
            return {
                **state,
                "result": {
                    "_objective_id": objective_id,
                    "status": "error",
                    "summary": "Unknown objective",
                    "artifacts": {},
                },
                "current_agent": "atlas",
            }

        # --------------------------------------------------
        # ✅ Correct identity check
        # --------------------------------------------------
        if spec.requires_concrete_identity and not has_concrete_identity(objective, state):
            log.warning(
                "NEMESIS DEFERRING: objective requires concrete identity "
                "but none is bound.\nObjective=%s",
                json.dumps(objective, indent=2),
            )

            return {
                **state,
                "needs_reference_resolution": True,
                "reference": json.dumps(
                    objective.get("target", {}).get("filter", {})
                ),
                "current_agent": "atlas",
            }

        # --------------------------------------------------
        # Execute
        # --------------------------------------------------
        try:
            raw_result = agent.run(state)
        except Exception as e:
            log.exception("NEMESIS EXECUTION FAILED")
            return {
                **state,
                "result": {
                    "_objective_id": objective_id,
                    "status": "error",
                    "summary": str(e),
                    "artifacts": {},
                },
                "current_agent": "atlas",
            }

        return {
            **state,
            "result": {
                **raw_result,
                "_objective_id": objective_id,
            },
            "current_agent": "atlas",
        }

    return nemesis_node
