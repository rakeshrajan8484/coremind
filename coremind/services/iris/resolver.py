import json
import re
from typing import Dict, Any, List, Optional, Union
from langchain_core.messages import SystemMessage, HumanMessage
from coremind.llms.factory import LLMFactory
from coremind.logging import get_logger
from coremind.services.iris.prompt import IRIS_PROMPT

log = get_logger("IRIS")


# ==================================================
# 🔒 SAFE JSON EXTRACTION
# ==================================================

def extract_json_object(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("IRIS did not return JSON")

    raw = text[start:end + 1]
    raw = re.sub(r":\s*00\.(\d+)", r": 0.\1", raw)

    return json.loads(raw)


# ==================================================
# 🧠 IRIS RESOLVER (STRICT, BULK-SAFE)
# ==================================================

class IrisResolver:
    """
    IRIS = reference resolution only.

    STRICT RULES:
    - Never invent IDs
    - Never broaden scope
    - Cardinality driven ONLY by selector
    """

    VERBS = {
        "mark", "delete", "remove", "open", "read", "unread",
        "show", "summarize", "get", "fetch"
    }

    STOPWORDS = {
        "from", "the", "email", "mail", "message",
        "an", "a", "to", "of", "in", "on", "as"
    }

    def __init__(self):
        self.llm = LLMFactory.iris()

    # --------------------------------------------------
    # 🔒 Constraint extraction (signals only)
    # --------------------------------------------------

    def _extract_constraints(self, reference: str) -> Dict[str, Any]:
        ref = reference.lower()

        constraints = {
            "sender_keywords": [],
            "subject_keywords": [],
            "local_date": None,
        }

        tokens = re.findall(r"[a-z0-9]+", ref)

        keywords = [
            t for t in tokens
            if t not in self.STOPWORDS
            and t not in self.VERBS
            and len(t) > 2
        ]

        constraints["sender_keywords"] = keywords

        # Date extraction (e.g. Dec 23)
        m = re.search(
            r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(\d{1,2})",
            ref,
        )
        if m:
            month_str, day = m.groups()
            month_map = {
                "jan": "01", "feb": "02", "mar": "03", "apr": "04",
                "may": "05", "jun": "06", "jul": "07", "aug": "08",
                "sep": "09", "oct": "10", "nov": "11", "dec": "12",
            }
            constraints["local_date"] = (month_map[month_str], int(day))

        return constraints

    # --------------------------------------------------
    # 🔒 Structured resolution ONLY
    # --------------------------------------------------

    def _resolve_structured(
        self,
        reference: str,
        candidates: List[Dict[str, Any]],
        selector: str,
    ) -> Optional[Dict[str, Any]]:

        constraints = self._extract_constraints(reference)
        scored: List[tuple[int, Dict[str, Any]]] = []

        for c in candidates:
            score = 0
            sender = (c.get("from") or "").lower()
            subject = (c.get("label") or "").lower()

            for kw in constraints["sender_keywords"]:
                if kw in sender:
                    score += 3
                elif kw in subject:
                    score += 1

            if constraints["local_date"]:
                month, day = constraints["local_date"]
                c_date = c.get("date", {}).get("local_date")
                if c_date:
                    _, c_month, c_day = c_date.split("-")
                    if c_month == month and int(c_day) == day:
                        score += 4

            if score > 0:
                scored.append((score, c))

        if not scored:
            return None

        scored.sort(key=lambda x: x[0], reverse=True)
        top_score = scored[0][0]
        top = [c for s, c in scored if s == top_score]

        # --------------------------------------------------
        # 🔒 selector = single
        # --------------------------------------------------
        if selector == "single":
            if len(top) == 1:
                return {
                    "resolved_to": top[0]["id"],
                    "confidence": 1.0,
                    "alternatives": [],
                }
            return None

        # --------------------------------------------------
        # 🔒 selector = subset | all → BULK ALLOWED
        # --------------------------------------------------
        if selector in {"subset", "all"}:
            ids = [c["id"] for c in top]

            if len(ids) == 1:
                return {
                    "resolved_to": ids,
                    "confidence": min(1.0, top_score / 6),
                    "alternatives": [],
                }

            return {
                "resolved_to": ids,
                "confidence": min(1.0, top_score / 6),
                "alternatives": [],
            }

        return None

    # --------------------------------------------------
    # 🔒 Main entry point
    # --------------------------------------------------

    def resolve(
        self,
        reference: str,
        candidates: List[Dict[str, Any]],
        selector: str = "single",
    ) -> Dict[str, Any]:

        if not reference or not candidates:
            return {
                "resolved_to": None,
                "confidence": 0.0,
                "alternatives": [],
            }

        structured = self._resolve_structured(
            reference=reference,
            candidates=candidates,
            selector=selector,
        )

        if structured is not None:
            log.warning("IRIS STRUCTURED RESOLUTION: %s", structured)
            return structured

        return {
            "resolved_to": None,
            "confidence": 0.0,
            "alternatives": [],
        }


# ==================================================
# 🔁 LANGGRAPH NODE (BULK-SAFE)
# ==================================================

def iris_node(state: Dict[str, Any]) -> Dict[str, Any]:
    log.warning(
        "IRIS RESOLVING | objective=%s | reference=%s",
        state.get("objective", {}).get("_intent"),
        state.get("reference"),
    )

    objective = state.get("objective")
    if not objective:
        return {
            **state,
            "needs_reference_resolution": False,
            "resolution_error": "IRIS called without objective",
        }

    resolver = IrisResolver()

    result = resolver.resolve(
        reference=state.get("reference"),
        candidates=state.get("candidates", []),
        selector=objective.get("target", {}).get("selector", "single"),
    )

    # NEVER leak resolution globally
    state.pop("resolved_id", None)

    if result["resolved_to"] is not None:
        return {
            **state,
            "objective": {
                **objective,
                "_resolved_id": result["resolved_to"],
                "_resolution_confidence": result["confidence"],
            },
            "needs_reference_resolution": False,
        }

    if result["alternatives"]:
        return {
            **state,
            "objective": {
                **objective,
                "_resolution_ambiguous": True,
                "_ambiguous_candidates": result["alternatives"],
            },
            "needs_reference_resolution": False,
        }

    return {
        **state,
        "objective": {
            **objective,
            "_resolution_none": True,
        },
        "needs_reference_resolution": False,
    }
