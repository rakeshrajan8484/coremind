import json
from typing import Dict, Any

from coremind.agents.nemesis.agent import NemesisAgent
from coremind.objectives.registry import OBJECTIVE_REGISTRY
from coremind.logging import get_logger

# 🔧 NEW: smart-home resolver
from coremind.agents.nemesis.resolvers.smart_home import resolve_smart_home_args

log = get_logger("NEMESIS.NODE")


# --------------------------------------------------
# 🔒 EMAIL: Concrete identity check (SINGLE + BULK SAFE)
# --------------------------------------------------
def has_concrete_identity(objective: Dict[str, Any], state: Dict[str, Any]) -> bool:
    """
    Concrete identity exists if the objective explicitly binds
    one or more entity identifiers.

    EMAIL ONLY. INTENT-AGNOSTIC.
    """

    target = objective.get("target") or {}
    filter_ = target.get("filter") or {}
    entity = target.get("entity")

    # ---- Draft ----
    if entity == "draft" and filter_.get("draft_id"):
        return True

    # ---- Message (single or bulk) ----
    if entity == "message":
        if filter_.get("id"):
            return True
        if isinstance(filter_.get("ids"), list) and filter_["ids"]:
            return True

    # ---- Thread ----
    if entity == "thread" and filter_.get("thread_id"):
        return True

    return False


# --------------------------------------------------
# 🔒 SMART HOME: Explicit device binding (HARD REQUIREMENT)
# --------------------------------------------------
def has_explicit_device_binding(objective: Dict[str, Any]) -> bool:
    """
    Smart-home objectives MUST bind an explicit device or device_group.
    No inference. No defaults. No filters.
    """

    target = objective.get("target") or {}

    if target.get("selector") != "explicit":
        return False

    entity = target.get("entity")
    if entity not in {"device", "device_group"}:
        return False

    # Device / group name MUST be explicitly present
    return bool(target.get("name"))


def make_nemesis_node():
    """
    NEMESIS = pure execution node.

    Responsibilities:
    - Execute EXACTLY ONE objective
    - NEVER plan
    - NEVER infer
    - NEVER retry
    - FAIL CLOSED for physical actions
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
        # No objective → return control
        # --------------------------------------------------
        if not objective:
            return {
                **state,
                "current_agent": "atlas",
            }

        objective_id = objective.get("_objective_id")

        # --------------------------------------------------
        # Resolve ObjectiveSpec (MANDATORY)
        # --------------------------------------------------
        key = (objective.get("domain"), objective.get("intent"))
        spec = OBJECTIVE_REGISTRY.get(key)

        if not spec:
            log.error("Unknown objective spec: %s", key)
            return {
                **state,
                "objective": None,
                "result": {
                    "_objective_id": objective_id,
                    "status": "error",
                    "summary": "Unknown objective",
                    "artifacts": {},
                },
                "current_agent": "atlas",
            }

        # --------------------------------------------------
        # 🔒 EMAIL identity gate
        # --------------------------------------------------
        if objective.get("domain") == "email":
            if spec.requires_concrete_identity and not has_concrete_identity(objective, state):
                log.warning(
                    "EMAIL objective deferred: missing concrete identity\n%s",
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
        # 🔒 SMART HOME explicit binding gate (FAIL CLOSED)
        # --------------------------------------------------
        if objective.get("domain") == "smart_home":
            if not has_explicit_device_binding(objective):
                log.error(
                    "SMART_HOME objective ABORTED: missing explicit device binding\n%s",
                    json.dumps(objective, indent=2),
                )
                return {
                    **state,
                    "objective": None,
                    "result": {
                        "_objective_id": objective_id,
                        "status": "skipped",
                        "summary": "Smart-home action skipped due to missing explicit device binding",
                        "artifacts": {
                            "force_done": True,
                        },
                    },
                    "current_agent": "atlas",
                }

            # --------------------------------------------------
            # 🔧 SMART HOME RESOLUTION STEP (THIS IS THE PLACE)
            # --------------------------------------------------
            try:
                constraints = objective.get("constraints") or {}
                resolved_constraints = resolve_smart_home_args(dict(constraints))
                objective["constraints"] = resolved_constraints
            except Exception as e:
                log.exception("SMART_HOME resolution failed")
                return {
                    **state,
                    "objective": None,
                    "result": {
                        "_objective_id": objective_id,
                        "status": "error",
                        "summary": f"Smart-home resolution failed: {e}",
                        "artifacts": {
                            "force_done": True,
                        },
                    },
                    "current_agent": "atlas",
                }

        # --------------------------------------------------
        # Execute (ONE STEP ONLY)
        # --------------------------------------------------
        try:
            raw_result = agent.run(state)
        except Exception as e:
            log.exception("NEMESIS EXECUTION FAILED")
            return {
                **state,
                "objective": None,
                "result": {
                    "_objective_id": objective_id,
                    "status": "error",
                    "summary": str(e),
                    "artifacts": {},
                },
                "current_agent": "atlas",
            }

        artifacts = raw_result.get("artifacts", {}) or {}

        # --------------------------------------------------
        # 🔑 FORCE-DONE HANDLING (STRICT)
        # --------------------------------------------------
        if artifacts.get("force_done"):
            # Smart-home MUST have executed a tool
            if objective.get("domain") == "smart_home":
                if not raw_result.get("tool_executed"):
                    log.error(
                        "INVALID force_done for smart_home without tool execution\n%s",
                        json.dumps(raw_result, indent=2),
                    )
                    artifacts.pop("force_done")

            if artifacts.get("force_done"):
                log.info("NEMESIS FORCE-DONE — terminating objective")
                return {
                    **state,
                    "objective": None,
                    "result": {
                        **raw_result,
                        "_objective_id": objective_id,
                        "_intent": objective.get("intent"),
                    },
                    "current_agent": "atlas",
                }

        # --------------------------------------------------
        # NORMAL TERMINATION
        # --------------------------------------------------
        return {
            **state,
            # Smart-home objectives NEVER re-enter
            "objective": None if objective.get("domain") == "smart_home" else state.get("objective"),
            "result": {
                **raw_result,
                "_objective_id": objective_id,
            },
            "current_agent": "atlas",
        }

    return nemesis_node
