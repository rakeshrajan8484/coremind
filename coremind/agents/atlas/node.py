from typing import Dict, Any, List
import json
import uuid
from datetime import datetime, timezone
import re
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from coremind.llms.factory import LLMFactory
from coremind.agents.atlas.prompt import ATLAS_PLANNER_PROMPT
from coremind.logging import get_logger

log = get_logger("ATLAS")
planner_llm = LLMFactory.atlas()

_DATE_FORMATS = [
    "%b %d",        # Jan 10
    "%B %d",        # January 10
    "%d %b",        # 10 Jan
    "%d %B",        # 10 January
    "%Y-%m-%d",     # 2026-01-10
]

KNOWN_ENTITIES = {"message", "thread", "draft"}

DISCOVERY_REQUIRED_INTENTS = {
    "update_read_state",
    "delete_message",
    "summarize_message",
    "send_draft",
    "delete_messages_bulk"
}

ORDINAL_MAP = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
}

# --------------------------------------------------
# Utilities
# --------------------------------------------------



EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

def _finalize_compose_constraints(obj: Dict[str, Any], state: Dict[str, Any]) -> None:
    if obj.get("intent") != "compose_message":
        return

    # ----------------------------
    # Resolve recipient (to)
    # ----------------------------
    target_filter = obj.get("target", {}).get("filter", {}) or {}

    to_email = (
        target_filter.get("to")
        or target_filter.get("sender")
    )

    if not to_email:
        # last resort: extract from intent_text
        intent_text = obj.get("intent_text", "")
        m = EMAIL_RE.search(intent_text)
        if m:
            to_email = m.group(0)

    if not to_email:
        raise ValueError("compose_message requires a recipient email (to)")

    # ----------------------------
    # Resolve body
    # ----------------------------
    constraints = obj.get("constraints")
    if not constraints.get("path"):
        constraints["path"] = "index.html"
    if isinstance(constraints, dict) and isinstance(constraints.get("body"), str):
        body = constraints["body"]
    else:
        intent_text = state.strip()
        log.info("Generating email body for intent_text: %s", intent_text)
        if not intent_text:
            raise ValueError("compose_message requires intent_text")

        prompt = f"""
You are writing the BODY of an email.

Rules:
- Do NOT include a Subject line
- Do NOT mention drafts or requests
- Write directly about the topic
- return the intent as the email body if the intent is not about any specific item

Topic:
{intent_text}
"""
        body = planner_llm.invoke(prompt).content.strip()
        log.info("Generated body: %s", body)
        # defensive cleanup
        body = re.sub(r"(?i)^subject:.*?\n+", "", body).strip()

    # ----------------------------
    # Final executable constraints
    # ----------------------------
    obj["constraints"] = {
        "to": to_email,
        "body": body,
    }



def _parse_json(content: str) -> Dict[str, Any]:
    parsed = json.loads(content[content.find("{"): content.rfind("}") + 1])
    log.debug("Planner raw JSON parsed: %s", parsed)
    return parsed


def _summarize_result(objective: Dict[str, Any], result: Dict[str, Any]) -> str:
    log.info(
        "Summarizing result | intent=%s | status=%s",
        objective.get("intent"),
        result.get("status"),
    )

    if result.get("status") != "success":
        return "I couldn’t complete that action."

    intent = objective.get("intent")

    if intent == "update_read_state":
        return "The email has been marked as read."
    if intent == "delete_message":
        return "The email has been deleted."
    if intent == "send_draft":
        return "The email has been sent."
    if intent == "summarize_message":
        return "Here is the summary of the email."

    return "Action completed successfully."

# --------------------------------------------------
# Selector & filter normalization
# --------------------------------------------------

def _normalize_selector(selector: Any) -> Dict[str, Any]:
    log.debug("Normalizing selector: %s", selector)

    if selector is None or selector == "single":
        return {"type": "ordinal", "value": 1}

    if isinstance(selector, dict):
        return selector

    if isinstance(selector, str):
        s = selector.lower()
        if s == "last":
            return {"type": "last"}
        if s == "all":
            return {"type": "all"}
        if s in ORDINAL_MAP:
            return {"type": "ordinal", "value": ORDINAL_MAP[s]}

    raise RuntimeError(f"Unsupported selector: {selector}")


def _normalize_filter(raw: Dict[str, Any]) -> Dict[str, Any]:
    filt: Dict[str, Any] = {}

    # --- sender ---
    sender = raw.get("sender") or raw.get("from") or raw.get("brand") or raw.get("to")
    if sender:
        s = sender.lower()
        for word in ORDINAL_MAP:
            s = s.replace(word, "")
        s = s.replace("email", "").strip()
        s = s.replace("from ", "").strip()
        if s:
            filt["sender"] = s

    # --- keywords ---
    keywords = raw.get("keywords")
    if keywords:
        filt["keywords"] = [k.lower() for k in keywords]

    # --- date (CRITICAL: preserve, don’t normalize yet) ---
    if "date" in raw:
        filt["date"] = raw["date"]

    return filt


def _parse_user_date(date_text: str) -> datetime | None:
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(date_text, fmt)
            # Year may be missing → assume current year
            if "%Y" not in fmt:
                dt = dt.replace(year=datetime.now(timezone.utc).year)
            return dt.date()
        except ValueError:
            continue
    return None

def _candidate_matches_date(candidate_dt: str, user_date: str) -> bool:
    if not candidate_dt or not user_date:
        return False

    try:
        cand = datetime.fromisoformat(
            candidate_dt.replace("Z", "+00:00")
        ).date()
    except Exception as e:
        log.warning("Failed to parse candidate date %s: %s", candidate_dt, e)
        return False

    # Parse user date (month/day only)
    parsed = None
    for fmt in ("%b %d", "%B %d", "%d %b", "%d %B", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(user_date, fmt).date()
            break
        except ValueError:
            continue

    if not parsed:
        log.warning("Failed to parse user date: %s", user_date)
        return False

    # 🔑 CRITICAL FIX:
    # If user did not specify a year, compare month/day only
    if parsed.year == 1900:  # default year from strptime
        return cand.month == parsed.month and cand.day == parsed.day

    # Full date comparison if year was specified
    return cand == parsed



def _apply_filter(candidates: List[Dict[str, Any]], filt: Dict[str, Any]) -> List[Dict[str, Any]]:
    log.info("Applying filter %s to %d candidates", filt, len(candidates))

    sender_filter = filt.get("sender")
    keywords_filter = filt.get("keywords", [])
    date_filter = filt.get("date")

    def match(c):
        frm = (c.get("from") or "").lower()
        lbl = (c.get("label") or "").lower()
     
        log.info(
            "MATCH DEBUG | id=%s | sender_filter='%s' | from='%s'",
            c.get("id"),
            sender_filter,
            frm,
        )

        # sender
        if sender_filter and sender_filter.lower() not in frm:
            return False

        # keywords
        for kw in keywords_filter:
            if kw not in frm and kw not in lbl:
                return False
        log.info(
            "DATE DEBUG | id=%s | raw_date=%s | internalDate=%s | full_date_obj=%s",
            c.get("id"),
            c.get("date"),
            c.get("internalDate"),
            c,
        )

        # date (CRITICAL FIX)
        if date_filter:
            local_label = c.get("date", {}).get("local_day_label", "").lower()
            if date_filter.lower() not in local_label:
                return False
        to_filter = filt.get("to")
        if to_filter:
            to_field = (c.get("to") or "").lower()
            if to_filter not in to_field:
                return False


        return True

    filtered = [c for c in candidates if match(c)]

    log.info(
        "Filter result: %d candidates matched (date=%s, sender=%s)",
        len(filtered),
        date_filter,
        sender_filter,
    )
    return filtered




def _sort_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    log.debug("Sorting %d candidates by date (newest first)", len(candidates))
    return sorted(
        candidates,
        key=lambda c: c.get("date", {}).get("utc_datetime", ""),
        reverse=True,
    )


def _apply_selector(candidates: List[Dict[str, Any]], selector: Dict[str, Any]) -> List[str]:
    log.info("Applying selector %s to %d candidates", selector, len(candidates))

    stype = selector["type"]

    if stype == "ordinal":
        idx = selector["value"] - 1
        if idx < 0 or idx >= len(candidates):
            raise RuntimeError("Selector index out of range")
        return [candidates[idx]["id"]]

    if stype == "last":
        return [candidates[-1]["id"]]

    if stype == "all":
        return [c["id"] for c in candidates]

    raise RuntimeError(f"Unknown selector type: {stype}")

# --------------------------------------------------
# ATLAS NODE (INSTRUMENTED)
# --------------------------------------------------

def atlas_node(state: Dict[str, Any]) -> Dict[str, Any]:
    log.info("=== ENTER ATLAS NODE ===")
    log.debug("Incoming state: %s", state)

    messages = state.get("messages", [])
    last_human = next(m for m in reversed(messages) if isinstance(m, HumanMessage))
    state["utterance"] = last_human.content
    state["terminated"] = False
    state.setdefault("objective_queue", [])

    current_obj = state.get("objective")
    result = state.get("result")
    

    # ==================================================
    # 1️⃣ CONSUME RESULT
    # ==================================================
    if result is not None:
        log.info("Consuming result for objective: %s", current_obj)

        intent = current_obj.get("intent") if current_obj else None
        if (
            current_obj
            and current_obj.get("operation", {}).get("type") == "delete"
            and not current_obj.get("_discovery_planned")
            and not current_obj.get("target", {}).get("filter", {}).get("ids")
        ):
            log.info("Planning discovery for DELETE objective (IDs missing)")

            discovery_obj = {
                "domain": "entity",
                "intent": "retrieve_candidates",
                "target": current_obj.get("target"),
                "operation": {"type": "retrieve", "value": "candidates"},
                "constraints": {"discovery_scope": "recent_any", "limit": 50},
                "_parent_objective": current_obj,
            }

            current_obj["_discovery_planned"] = True

            return {
                **state,
                "objective": discovery_obj,
                
                "result": None,
            }

        if intent == "retrieve_candidates" and result.get("status") == "success":
            log.info("Discovery result received")

            candidates = result.get("artifacts", {}).get("candidates", [])
            original = current_obj.get("_parent_objective")
            if not original:
                log.error("Discovery result has no parent objective")
                return state


            log.debug("Original deferred objective: %s", original)

            

            filt = _normalize_filter(original.get("target", {}).get("filter", {}))
            filtered = _apply_filter(candidates, filt)

            if not filtered:
                log.warning("No candidates matched after filtering")
                return {
                    **state,
                    "messages": messages + [AIMessage("No matching emails found.")],
                    "objective": None,
                    "objective_queue": [],
                    "terminated": True,
                    "result": None,
                }

            ordered = _sort_candidates(filtered)
            raw_selector = original.get("target", {}).get("selector")
            if len(filtered) == 1:
                resolved_ids = [filtered[0]["id"]]
            else:
                selector = _normalize_selector(raw_selector)
                resolved_ids = _apply_selector(ordered, selector)


            log.info("Resolved message IDs: %s", resolved_ids)

            original["target"] = {
                "entity": "message",
                "filter": {"ids": resolved_ids},
            }

            return {
                **state,
                "objective": original,
                
                "result": None,
            }

        summary = _summarize_result(current_obj, result)
        log.info("Execution complete, terminating ATLAS")

        return {
            **state,
            "messages": messages + [AIMessage(summary)],
            "objective": None,
            "objective_queue": [],
            "terminated": True,
            "result": None,
        }

    # ==================================================
    # 2️⃣ IDS PRESENT → DIRECT EXECUTION
    # ==================================================
    if current_obj and current_obj.get("target", {}).get("filter", {}).get("ids"):
        log.info("Objective already resolved with IDs, executing directly")
        return {
            **state,
            "objective": current_obj,
            
            "result": None,
        }

    # ==================================================
    # 3️⃣ NEW REQUEST → PLANNING
    # ==================================================
    if not current_obj and not state["objective_queue"]:
        log.info("Planning new objectives for utterance: %s", state["utterance"])
        print("LLM TYPE:", type(planner_llm))

        planner_response = planner_llm.invoke(
            [SystemMessage(ATLAS_PLANNER_PROMPT), HumanMessage(state["utterance"])]
        )

        log.debug("Planner raw response: %s", planner_response.content)

        try:
            raw = _parse_json(planner_response.content)
        except Exception as e:
            log.error("❌ Failed to parse planner response: %s", e)
            return {
                **state,
                "messages": messages + [AIMessage("I couldn’t understand that request.")],
                "terminated": True,
            }

        objectives = raw.get("objectives", [])

        # 🔥 FIX: handle empty objectives
        if not objectives:
            log.warning("⚠️ Planner returned no objectives")

            return {
                **state,
                "messages": messages + [
                    AIMessage("I couldn’t find an action to perform. Can you rephrase?")
                ],
                "objective": None,
                "objective_queue": [],
                "terminated": True,
            }

        # ✅ Normal flow
        for o in objectives:
            o["_objective_id"] = str(uuid.uuid4())
            o["_intent"] = o.get("intent_text", "")
            o["_discovery_planned"] = False

            try:
                _finalize_compose_constraints(o, state["utterance"])
            except Exception as e:
                log.warning("Constraint finalize failed: %s", e)

            target = o.get("target", {})
            entity = target.get("entity")

            # 🔥 FIX: Only apply for EMAIL domain
            if o.get("domain") == "email":
                if entity and entity not in KNOWN_ENTITIES:
                    log.debug("Unknown entity '%s' → coercing to message sender", entity)
                    target["entity"] = "message"
                    target.setdefault("filter", {})["sender"] = entity

            log.info("Queued objective: %s", o)
            state["objective_queue"].append(o)

        # 🔥 SAFE POP
        if not state["objective_queue"]:
            log.error("❌ Objective queue still empty after processing")

            return {
                **state,
                "messages": messages + [AIMessage("Something went wrong while planning.")],
                "terminated": True,
            }

        next_obj = state["objective_queue"].pop(0)
        log.info("Dispatching objective: %s", next_obj)

        return {
            **state,
            "objective": next_obj,
        }
    # ==================================================
    # 4️⃣ DEFERRAL → DISCOVERY (ONCE)
    # ==================================================
    if (
        current_obj
        and current_obj.get("intent") in DISCOVERY_REQUIRED_INTENTS
        and not current_obj.get("_discovery_planned")
        and not current_obj.get("target", {}).get("filter", {}).get("ids")
    ):
        log.info("Planning discovery for objective: %s", current_obj)

        discovery_obj = {
            "domain": "entity",
            "intent": "retrieve_candidates",
            "target": current_obj.get("target"),
            "operation": {"type": "retrieve", "value": "candidates"},
            "constraints": {"discovery_scope": "recent_any", "limit": 10},
        }

        current_obj["_discovery_planned"] = True
        discovery_obj["_parent_objective"] = current_obj
 

        return {
            **state,
            "objective": discovery_obj,
            
            "result": None,
        }

    log.debug("No state transition, returning unchanged state")
    return state
