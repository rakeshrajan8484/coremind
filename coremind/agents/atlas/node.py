from typing import Dict, Any
import json
import uuid

from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from coremind.llms.factory import LLMFactory
from coremind.agents.atlas.prompt import (
    ATLAS_PLANNER_PROMPT,
    DISCOVERY_PLANNER_PROMPT,
)
from coremind.logging import get_logger
from coremind.objectives.registry import OBJECTIVE_REGISTRY

log = get_logger("ATLAS")
planner_llm = LLMFactory.atlas()


# --------------------------------------------------
# 🔧 Utilities
# --------------------------------------------------
def _parse_json(content: str) -> Dict[str, Any]:
    return json.loads(
        content[content.find("{"): content.rfind("}") + 1]
    )


def _apply_hard_constraints(
    candidates: list[Dict[str, Any]],
    constraints: Dict[str, Any] | None,
) -> list[Dict[str, Any]]:
    if not constraints:
        return candidates

    filtered = candidates

    if "date" in constraints:
        target = constraints["date"].strip().lower()

        def _match_date(c):
            return (
                c.get("date", {})
                 .get("local_day_label", "")
                 .strip()
                 .lower()
                == target
            )

        filtered = [c for c in filtered if _match_date(c)]

    return filtered


def _build_reference(obj: Dict[str, Any]) -> str:
    return json.dumps({
        **obj.get("target", {}).get("filter", {}),
        **(obj.get("constraints") or {}),
    })


# --------------------------------------------------
# 🧠 ATLAS NODE (CONTRACT SAFE)
# --------------------------------------------------
def atlas_node(state: Dict[str, Any]) -> Dict[str, Any]:
    log.info("Entered ATLAS node with state: %s", state)

    messages = state.get("messages")
    if not messages:
        raise RuntimeError("Contract violation: messages missing")

    # --------------------------------------------------
    # 🛑 HARD TERMINATION
    # --------------------------------------------------
    if state.get("terminated"):
        return state

    # --------------------------------------------------
    # 🧠 ALWAYS USE LATEST UTTERANCE (CHAT MODE)
    # --------------------------------------------------
    last = next(m for m in reversed(messages) if isinstance(m, HumanMessage))
    state["utterance"] = last.content

    utterance = state["utterance"]
    current_obj = state.get("objective")
    result = state.get("result")

    state.setdefault("objective_queue", [])

    # ==================================================
    # 1️⃣ CONSUME NEMESIS / IRIS RESULT
    # ==================================================
    if result is not None:
        artifacts = result.get("artifacts", {})
        raw = artifacts.get("raw_data", {})

        # ---- persist draft id ----
        if raw.get("status") == "drafted":
            state["last_draft_id"] = raw.get("draft_id")

        # ---- SUCCESS → continue chat (NO termination) ----
        if result.get("status") == "success":
            return {
                **state,
                "messages": messages + [
                    AIMessage(result.get("summary", "Action completed successfully."))
                ],
                "objective": None,
                "objective_queue": [],
                "result": None,
                "current_agent": "atlas",
            }

        # ---- FAILURE → terminal ----
        return {
            **state,
            "messages": messages + [
                AIMessage(result.get("summary", "Action failed."))
            ],
            "objective": None,
            "objective_queue": [],
            "terminated": True,
        }

    # ==================================================
    # 🚫 AMBIGUOUS IRIS RESULT → TERMINATE
    # ==================================================
    if current_obj and current_obj.get("_resolution_ambiguous"):
        alts = current_obj.get("_ambiguous_candidates", [])
        msg = "Multiple matching emails were found. Please specify which one:\n"
        for a in alts:
            msg += f"- {a['entity_id']}\n"

        return {
            **state,
            "messages": messages + [AIMessage(msg)],
            "objective": None,
            "objective_queue": [],
            "terminated": True,
        }

    # ==================================================
    # 🔒 SEND_DRAFT: NEVER GO TO IRIS (CRITICAL FIX)
    # ==================================================
    if current_obj and current_obj.get("intent") == "send_draft":
        # 🔒 hard purge IRIS-related state
        for k in [
            "needs_reference_resolution",
            "reference",
            "_resolution_none",
            "_resolution_ambiguous",
            "_ambiguous_candidates",
            "candidates",
        ]:
            state.pop(k, None)

        # 🔒 bind draft id if missing
        target = current_obj.setdefault("target", {})
        filt = target.setdefault("filter", {})

        if "draft_id" not in filt:
            draft_id = state.get("last_draft_id")
            if not draft_id:
                raise RuntimeError("No drafted email available to send")
            filt["draft_id"] = draft_id

        current_obj["_discovery_planned"] = True

        return {
            **state,
            "objective": current_obj,
            "current_agent": "nemesis",
            "result": None,
        }

    # ==================================================
    # 2️⃣ PROMOTE RESOLVED DISCOVERY → EXECUTION
    # ==================================================
    if current_obj and current_obj.get("_resolved_id"):
        rid = current_obj["_resolved_id"]

        planner_response = planner_llm.invoke(
            [
                SystemMessage(ATLAS_PLANNER_PROMPT),
                HumanMessage(f"{current_obj['_intent']}\nResolved target ID: {rid}"),
            ]
        )

        raw = _parse_json(planner_response.content)
        exec_obj = raw["objectives"][0]

        exec_obj["_objective_id"] = str(uuid.uuid4())
        exec_obj["_intent"] = current_obj["_intent"]
        exec_obj.setdefault("target", {}).setdefault("filter", {})["id"] = rid

        # 🔒 clear resolution state
        for k in [
            "_resolved_id",
            "_resolution_none",
            "_resolution_ambiguous",
            "_ambiguous_candidates",
            "candidates",
            "needs_reference_resolution",
            "reference",
        ]:
            state.pop(k, None)

        state["objective_queue"] = []

        return {
            **state,
            "objective": exec_obj,
            "current_agent": "nemesis",
            "result": None,
        }

    # ==================================================
    # 3️⃣ INITIAL PLANNING
    # ==================================================
    if not current_obj and not state["objective_queue"]:
        planner_response = planner_llm.invoke(
            [
                SystemMessage(ATLAS_PLANNER_PROMPT),
                HumanMessage(utterance),
            ]
        )

        raw = _parse_json(planner_response.content)
        objectives = raw.get("objectives")

        if not objectives:
            raise RuntimeError("Planner contract violation: objectives[] required")

        for o in objectives:
            o["_objective_id"] = str(uuid.uuid4())
            o["_intent"] = o["intent_text"]
            o["_discovery_planned"] = False

            # 🔒 bind draft id early for send_draft
            if o.get("intent") == "send_draft":
                draft_id = state.get("last_draft_id")
                if not draft_id:
                    raise RuntimeError("No drafted email available to send")
                o.setdefault("target", {}).setdefault("filter", {})[
                    "draft_id"
                ] = draft_id

            state["objective_queue"].append(o)

        return {
            **state,
            "objective": state["objective_queue"].pop(0),
            "current_agent": "atlas",
        }

    # ==================================================
    # 4️⃣ DISCOVERY PLANNING (NON-CREATE ONLY)
    # ==================================================
    if current_obj and not current_obj.get("_discovery_planned"):
        spec = OBJECTIVE_REGISTRY.get(
            (current_obj.get("domain"), current_obj.get("intent"))
        )

        if spec and spec.requires_concrete_identity:
            discovery_response = planner_llm.invoke(
                [
                    SystemMessage(DISCOVERY_PLANNER_PROMPT),
                    HumanMessage(current_obj["_intent"]),
                ]
            )

            raw = _parse_json(discovery_response.content)

            for d in raw.get("discoveries", []):
                state["objective_queue"].append({
                    "_objective_id": str(uuid.uuid4()),
                    "_intent": current_obj["_intent"],
                    "domain": "entity",
                    "intent": "retrieve_candidates",
                    "target": d["target"],
                    "operation": {"type": "retrieve", "value": "candidates"},
                    "constraints": {
                        **d.get("constraints", {}),
                        "discovery_scope": "recent_any",
                    },
                })

            current_obj["_discovery_planned"] = True

            return {
                **state,
                "objective": state["objective_queue"].pop(0),
                "current_agent": "nemesis",
                "result": None,
            }

    # ==================================================
    # 5️⃣ FINAL DISPATCH
    # ==================================================
    if current_obj:
        return {
            **state,
            "objective": current_obj,
            "current_agent": "nemesis",
            "result": None,
        }

    return state
