# coremind/services/iris/resolver.py

import json
import re
from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from coremind.llms.factory import LLMFactory
from coremind.logging import get_logger

log = get_logger("IRIS")

# ==================================================
# 🔒 IRIS SYSTEM PROMPT (STRICT CONTRACT)
# ==================================================

IRIS_PROMPT = """
You are IRIS, a deterministic reference resolution service.

Your ONLY responsibility:
- Resolve a natural language reference to ONE entity_id from the given candidates.

STRICT RULES (VIOLATION = FAILURE):
- You MUST choose entity_id ONLY from the provided candidates.
- You MUST return null if no candidate clearly matches.
- You MUST NOT invent, infer, or modify entity_ids.
- You MUST prioritize explicit signals:
  1. Dates (Nov 5, yesterday, last Monday)
  2. Sender / source (LinkedIn, Adobe, GitHub)
  3. Subject keywords
- If multiple candidates partially match, return them as alternatives.

You do NOT:
- Decide what happens next
- Execute tools
- Ask the user questions

Return JSON ONLY in the following schema:

{
  "resolved_to": "<entity_id or null>",
  "confidence": <float between 0 and 1>,
  "alternatives": [
    {"entity_id": "<id>", "confidence": <float>}
  ]
}
"""

# ==================================================
# 🔒 SAFE JSON EXTRACTION
# ==================================================

def extract_json_object(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("IRIS did not return JSON")

    raw = text[start:end + 1]

    # Normalize illegal floats like 00.25
    raw = re.sub(r":\s*00\.(\d+)", r": 0.\1", raw)

    return json.loads(raw)

# ==================================================
# 🧠 IRIS RESOLVER (PURE, STATELESS)
# ==================================================

class IrisResolver:
    """
    IRIS = reference resolution only.

    - Stateless
    - Deterministic
    - No side effects
    """

    def __init__(self):
        self.llm = LLMFactory.iris()

    # --------------------------------------------------
    # 🔒 Structured deterministic resolution
    # --------------------------------------------------

    def _extract_constraints(self, reference: str) -> Dict[str, Any]:
        ref = reference.lower()

        constraints = {
            "sender_keywords": [],
            "subject_keywords": [],
            "local_date": None,
        }

        # ----------------------------
        # Sender / provider keywords
        # ----------------------------
        STOPWORDS = {
            "from", "the", "email", "mail", "message",
            "delete", "remove", "open", "show", "latest",
            "an", "a", "to", "of", "in"
        }

        tokens = re.findall(r"[a-z0-9]+", ref)

        keywords = [t for t in tokens if t not in STOPWORDS and len(t) > 2]

        constraints["sender_keywords"] = keywords

        # ----------------------------
        # Date extraction (Dec 30)
        # ----------------------------
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


    def _resolve_structured(
        self,
        reference: str,
        candidates: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:

        constraints = self._extract_constraints(reference)

        scored = []

        for c in candidates:
            score = 0

            sender = (c.get("from") or "").lower()
            subject = (c.get("label") or "").lower()

            # ----------------------------
            # Sender keyword match
            # ----------------------------
            for kw in constraints["sender_keywords"]:
                if kw in sender:
                    score += 2
                if kw in subject:
                    score += 1

            # ----------------------------
            # Date match
            # ----------------------------
            if constraints["local_date"]:
                month, day = constraints["local_date"]
                c_date = c.get("date", {}).get("local_date")
                if c_date:
                    _, c_month, c_day = c_date.split("-")
                    if c_month == month and int(c_day) == day:
                        score += 3

            if score > 0:
                scored.append((score, c))

        if not scored:
            return None

        scored.sort(key=lambda x: x[0], reverse=True)

        top_score = scored[0][0]
        top_matches = [c for s, c in scored if s == top_score]

        if len(top_matches) == 1:
            return {
                "resolved_to": top_matches[0]["id"],
                "confidence": min(1.0, top_score / 5),
                "alternatives": [],
            }

        return {
            "resolved_to": None,
            "confidence": 0.5,
            "alternatives": [
                {"entity_id": c["id"], "confidence": 0.5}
                for c in top_matches
            ],
        }


    # --------------------------------------------------
    # 🔒 Main resolve entry point
    # --------------------------------------------------

    def resolve(
        self,
        reference: str,
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        if not reference or not candidates:
            return {
                "resolved_to": None,
                "confidence": 0.0,
                "alternatives": [],
            }

        # --- 1️⃣ Structured resolution FIRST ---
        structured = self._resolve_structured(reference, candidates)
        if structured is not None:
            log.warning("IRIS STRUCTURED RESOLUTION: %s", structured)
            return structured

        # --- 2️⃣ LLM fallback ---
        candidate_ids = {c["id"] for c in candidates if "id" in c}

        payload = {
            "reference": reference,
            "candidates": [
                {
                    "entity_id": c.get("id"),
                    "from": c.get("from"),
                    "subject": c.get("label"),
                    "date": c.get("date"),
                }
                for c in candidates
            ],
        }

        response = self.llm.invoke(
            [
                SystemMessage(content=IRIS_PROMPT),
                HumanMessage(content=json.dumps(payload)),
            ]
        )

        log.warning("IRIS RAW OUTPUT:\n%s", response.content)

        data = extract_json_object(response.content)

        resolved_to = data.get("resolved_to")
        confidence = float(data.get("confidence", 0.0))
        alternatives = data.get("alternatives", [])

        # --- Post-validation ---
        if resolved_to not in candidate_ids:
            resolved_to = None
            confidence = 0.0

        valid_alternatives = []
        for alt in alternatives:
            eid = alt.get("entity_id")
            if eid in candidate_ids:
                valid_alternatives.append(
                    {
                        "entity_id": eid,
                        "confidence": float(alt.get("confidence", 0.0)),
                    }
                )

        return {
            "resolved_to": resolved_to,
            "confidence": confidence,
            "alternatives": valid_alternatives,
        }

# ==================================================
# 🔁 LANGGRAPH NODE (STATE TRANSFORMER ONLY)
# ==================================================

def iris_node(state: Dict[str, Any]) -> Dict[str, Any]:
    log.warning(
        "IRIS NODE | reference=%s | candidates=%d",
        state.get("reference"),
        len(state.get("candidates", [])),
    )

    resolver = IrisResolver()

    result = resolver.resolve(
        reference=state.get("reference"),
        candidates=state.get("candidates", []),
    )

    if result["resolved_to"]:
        log.warning("IRIS RESOLUTION RESULT with resolved_id: %s", result)
        return {
            **state,
            "resolved_id": result["resolved_to"],
            "needs_reference_resolution": False,
        }

    if result["alternatives"]:
        return {
            **state,
            "resolution_ambiguous": True,
            "ambiguous_candidates": result["alternatives"],
            "needs_reference_resolution": False,
        }

    return {
        **state,
        "resolution_none": True,
        "needs_reference_resolution": False,
    }
