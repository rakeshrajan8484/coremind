from typing import Dict, Any
import json
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage

from coremind.llms.factory import LLMFactory
from coremind.agents.atlas.prompt import (
    ATLAS_PLANNER_PROMPT,
    ATLAS_RESPONSE_PROMPT,
    DISCOVERY_PLANNER_PROMPT,
)
from coremind.logging import get_logger
from coremind.objectives.registry import OBJECTIVE_REGISTRY

log = get_logger("ATLAS")

planner_llm = LLMFactory.atlas()
summary_llm = LLMFactory.atlasSummary()


# -------------------------------------------------
# 🔎 Reference extraction (IRIS-safe)
# -------------------------------------------------
def extract_reference_text(intent: str) -> str | None:
    text = intent.lower()
    if "email" in text:
        text = text.split("email", 1)[1]

    for stop in [
        "summarize",
        "mark",
        "delete",
        "remove",
        "as read",
        "as unread",
    ]:
        text = text.replace(stop, "")

    return text.strip() or None

def objective_signature(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True)

# -------------------------------------------------
# 🧠 ATLAS NODE
# -------------------------------------------------
def atlas_node(state: Dict[str, Any]) -> Dict[str, Any]:
    log.info("Entered ATLAS node with state: %s", state)

    # -------------------------------------------------
    # 🛑 Hard termination guard
    # -------------------------------------------------
    if state.get("terminated"):
        return state

    messages = state.get("messages", [])
    result = state.get("result")

    if not messages:
        raise ValueError("CoreMind contract violation: messages missing")

    # -------------------------------------------------
    # 0️⃣ Capture intent ONCE
    # -------------------------------------------------
    if "intent" not in state:
        last = next(m for m in reversed(messages) if isinstance(m, HumanMessage))
        state["intent"] = last.content
        log.info("Captured intent: %s", state["intent"])

    intent = state["intent"]

    # =================================================
    # 1️⃣ CONSUME NEMESIS RESULT
    # =================================================
    if result is not None:
        log.info("Result in atlas: %s", result)
        artifacts = result.get("artifacts", {})

        # -------------------------------------------------
        # 🔍 DISCOVERY RESULT (retrieve_candidates)
        # -------------------------------------------------
        if "candidates" in artifacts:
            candidates = artifacts["candidates"]

            log.error("========== CANDIDATES DUMP ==========")
            for i, c in enumerate(candidates):
                log.error(
                    "[%d] id=%s | from=%s | subject=%s",
                    i,
                    c.get("id"),
                    c.get("from"),
                    c.get("label"),
                )
            log.error("====================================")

            if not candidates:
                return {
                    **state,
                    "messages": messages + [
                        AIMessage("I couldn’t find any matching email.")
                    ],
                    "terminated": True,
                    "objective": None,
                }

            # -------------------------------------------------
            # 🔑 Deterministic resolution (brand/sender)
            # -------------------------------------------------

            objective = state.get("objective")

            # 🔒 Hard gate: do NOT attempt identity resolution
            # - if objective is gone
            # - OR if reference resolution already ran
            if objective is None or state.get("needs_reference_resolution") is False:
                log.info(
                    "Skipping deterministic resolution "
                    "(objective=%s, needs_reference_resolution=%s)",
                    objective is not None,
                    state.get("needs_reference_resolution"),
                )
            else:
                target_filter = objective.get("target", {}).get("filter", {})
                brand = target_filter.get("brand")

                log.info("Attempting deterministic resolution via brand: %s", brand)

                if brand:
                    brand = brand.lower()
                    matches = [
                        c for c in candidates
                        if brand in (c.get("from") or "").lower()
                    ]

                    if len(matches) == 1:
                        log.info(
                            "Resolved deterministically via brand: %s",
                            matches[0]["id"],
                        )
                        return {
                            **state,
                            "resolved_id": matches[0]["id"],
                            "result": None,
                            "objective": None,
                            "current_agent": "atlas",
                        }


            # Single candidate fallback
            if len(candidates) == 1:
                log.info("Resolved deterministically (single candidate)")
                return {
                    **state,
                    "resolved_id": candidates[0]["id"],
                    "result": None,
                    "objective": None,
                    "current_agent": "atlas",
                }

            # -------------------------------------------------
            # 🧠 IRIS only if truly ambiguous
            # -------------------------------------------------
            if state.get("resolution_ambiguous"):
                log.info("IRIS ambiguity already reached — not re-requesting reference resolution")
                return {
                    **state,
                    "result": None,
                    "objective": None,
                    "current_agent": "atlas",
                }

            reference = extract_reference_text(intent)

            return {
                **state,
                "candidates": candidates,
                "reference": reference,
                "needs_reference_resolution": True,
                "result": None,
            }

        # -------------------------------------------------
        # 🗑️ DESTRUCTIVE ACTION TERMINATION (DELETE / MARK)
        # -------------------------------------------------
        if result.get("status") == "success" and state.get("resolved_id"):
            log.info("Destructive action completed — terminating")
            state.pop("last_objective_signature", None)
            return {
                **state,
                "messages": messages + [
                    AIMessage("The action has been completed successfully.")
                ],
                "terminated": True,
                "objective": None,
                "current_agent": "atlas",
            }

        # -------------------------------------------------
        # 📄 CONTENT RESULT (summarize / read)
        # -------------------------------------------------
        raw = artifacts.get("raw_data")
        summary = result.get("summary")
        # -------------------------------------------------
        # 🛑 HARD STOP: resolved objective requiring identity
        # -------------------------------------------------
        if state.get("resolved_id") and state.get("objective") is None:
            log.info(
                "Resolved ID present (%s) and no pending objective — executing directly",
                state["resolved_id"],
            )

            # Reconstruct objective ONCE with resolved ID
            planner_response = planner_llm.invoke(
                [
                    SystemMessage(content=ATLAS_PLANNER_PROMPT),
                    HumanMessage(
                        content=f"{intent}\nResolved target ID: {state['resolved_id']}"
                    ),
                ]
            )

            obj = json.loads(
                planner_response.content[
                    planner_response.content.find("{"):
                    planner_response.content.rfind("}") + 1
                ]
            )

            obj.setdefault("target", {}).setdefault("filter", {})["id"] = state["resolved_id"]

            sig = objective_signature(obj)

            if state.get("last_objective_signature") == sig:
                log.info("Objective unchanged — stopping replanning to avoid loop")
                return {
                    **state,
                    "objective": None,
                    "current_agent": "atlas",
                }

            return {
                **state,
                "objective": obj,
                "last_objective_signature": sig,
                "current_agent": "nemesis",
            }


        if raw:
            response = planner_llm.invoke(
                [
                    SystemMessage(content=ATLAS_RESPONSE_PROMPT),
                    *messages,
                    AIMessage(content=f"OBSERVATION: {raw}"),
                    HumanMessage(content=intent),
                ]
            )
            final = response.content.strip()
        else:
            final = summary_llm.invoke(
                [HumanMessage(content=summary)]
            ).content.strip()

        return {
            **state,
            "messages": messages + [AIMessage(final)],
            "terminated": True,
            "objective": None,
            "current_agent": "atlas",
        }

    # =================================================
    # 2️⃣ RESOLVED ID → REPLAN (NO DISCOVERY)
    # =================================================
    if state.get("resolved_id"):
        rid = state["resolved_id"]
        log.info("Resolved ID present (%s) — replanning", rid)

        intent_with_id = f"{intent}\nResolved target ID: {rid}"

        planner_response = planner_llm.invoke(
            [
                SystemMessage(content=ATLAS_PLANNER_PROMPT),
                HumanMessage(content=intent_with_id),
            ]
        )

        obj = json.loads(
            planner_response.content[
                planner_response.content.find("{"):
                planner_response.content.rfind("}") + 1
            ]
        )

        obj.setdefault("target", {}).setdefault("filter", {})["id"] = rid

        return {
            **state,
            "objective": obj,
            "current_agent": "nemesis",
        }

    # =================================================
    # 3️⃣ INITIAL PLANNING
    # =================================================
    planner_response = planner_llm.invoke(
        [
            SystemMessage(content=ATLAS_PLANNER_PROMPT),
            HumanMessage(content=intent),
        ]
    )

    obj = json.loads(
        planner_response.content[
            planner_response.content.find("{"):
            planner_response.content.rfind("}") + 1
        ]
    )

    spec = OBJECTIVE_REGISTRY.get((obj.get("domain"), obj.get("intent")))

    # =================================================
    # 4️⃣ DISCOVERY ONLY IF ID REQUIRED AND NOT RESOLVED
    # =================================================
    if (
        spec
        and spec.requires_concrete_identity
        and state.get("needs_reference_resolution") is not False
        and not state.get("resolution_ambiguous")
    ):
        log.info("Concrete identity required — starting discovery")

        discovery_response = planner_llm.invoke(
            [
                SystemMessage(content=DISCOVERY_PLANNER_PROMPT),
                HumanMessage(content=intent),
            ]
        )

        raw = json.loads(
            discovery_response.content[
                discovery_response.content.find("{"):
                discovery_response.content.rfind("}") + 1
            ]
        )

        return {
            **state,
            "objective": {
                "domain": "entity",
                "intent": "retrieve_candidates",
                "target": raw["target"],
                "operation": {"type": "retrieve", "value": "candidates"},
                "constraints": {
                    "limit": 10,
                    "discovery_scope": "recent_any",
                },
            },
            "current_agent": "nemesis",
        }

     
    # =================================================
    # 5️⃣ DIRECT EXECUTION (ONLY IF EXECUTABLE)
    # =================================================

    # 🔒 If identity is required but not resolved, do NOT send to Nemesis
    if spec and spec.requires_concrete_identity and not state.get("resolved_id"):
        log.info(
            "Objective requires concrete identity but none resolved — stopping Atlas"
        )
        return {
            **state,
            "objective": None,
            "current_agent": "atlas",
        }

    return {
        **state,
        "objective": obj,
        "current_agent": "nemesis",
    }

