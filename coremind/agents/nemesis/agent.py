from typing import Dict, Any, List
import json

from coremind.agents.nemesis.adapters.email import email_to_candidate
from coremind.llms.factory import LLMFactory
import coremind.agents.nemesis.tools  # force tool registration
from coremind.agents.nemesis.tools.registry import TOOL_REGISTRY
from coremind.logging import get_logger

log = get_logger("NEMESIS")


# --------------------------------------------------
# 🔒 Single-shot (terminal) objectives
# --------------------------------------------------
TERMINAL_INTENTS = {
    ("email", "update_read_state"),
    ("email", "delete_message"),
    ("email", "summarize"),
    ("email", "compose_message"),
    ("email", "send_draft"),
}


class NemesisAgent:
    """
    Execution-only agent.

    - No planning
    - No semantic resolution
    - Deterministic execution
    """

    def __init__(self):
        self.llm = LLMFactory.nemesis()
        self.tools = TOOL_REGISTRY

    def _extract_concrete_id(
        self, objective: Dict[str, Any], state: Dict[str, Any]
    ) -> str | None:
        """
        Canonical identity extraction.
        Supports IRIS resolution and domain-specific IDs.
        """

        if state.get("resolved_id"):
            return state["resolved_id"]

        target = objective.get("target") or {}
        filter_ = target.get("filter") or {}
        entity = target.get("entity")

        if entity == "draft":
            return filter_.get("draft_id")

        if entity == "message":
            return filter_.get("id")

        if entity == "thread":
            return filter_.get("thread_id")

        return None

    # --------------------------------------------------
    # Public entry
    # --------------------------------------------------
    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self._reset_run_state()
        self._validate_state(state)

        objective = state["objective"]
        domain = objective.get("domain")
        intent = objective.get("intent")

        # --------------------------------------------------
        # 🔒 CANONICAL ID NORMALIZATION
        # --------------------------------------------------
        resolved_id = self._extract_concrete_id(objective, state)


        # --------------------------------------------------
        # 🔒 HARD TERMINAL: candidate retrieval
        # --------------------------------------------------
        if (domain, intent) == ("entity", "retrieve_candidates"):
            log.info("NEMESIS handling retrieve_candidates (terminal)")
            candidates = self._retrieve_candidates(objective)
            return {
                "status": "success",
                "summary": "Candidates retrieved",
                "artifacts": {"candidates": candidates},
            }

        # --------------------------------------------------
        # 🔒 HARD TERMINAL: CREATE (NO LLM, NO LOOP)
        # --------------------------------------------------
        if objective.get("operation", {}).get("type") == "create":
            tool = self._select_create_tool(objective)

            args = dict(objective.get("constraints") or {})
            self.tools.validate_args(tool.name, args)

            log.warning(
                "NEMESIS TOOL CALL | tool=%s | args=%r",
                tool.name,
                args,
            )

            result = tool.run(args)

            return {
                "status": "success",
                "summary": "Email draft created successfully.",
                "artifacts": {"raw_data": result},
            }
        # --------------------------------------------------
        # 🔒 HARD TERMINAL: SEND DRAFT (NO LLM)
        # --------------------------------------------------
        if (domain, intent) == ("email", "send_draft"):
            draft_id = resolved_id
            if not draft_id:
                raise ValueError("send_draft requires draft_id")

            tool = self.tools.get("send_draft")

            args = {"id": draft_id}
            self.tools.validate_args("send_draft", args)

            log.warning(
                "NEMESIS TOOL CALL | tool=send_draft | args=%r",
                args,
            )

            result = tool.run(args)

            return {
                "status": "success",
                "summary": "Draft sent successfully.",
                "artifacts": {"raw_data": result},
            }

        # --------------------------------------------------
        # 🔒 HARD CONTRACT: resolved identity required
        # --------------------------------------------------
        target = objective.get("target", {})
        if target.get("selector") == "single" and not resolved_id:
            raise ValueError(
                "NEMESIS cannot execute objective requiring identity "
                "without a concrete ID"
            )

        terminal = (domain, intent) in TERMINAL_INTENTS

        # --------------------------------------------------
        # Normal execution loop (LLM-driven)
        # --------------------------------------------------
        while True:
            step = self._decide_next_step(objective)

            if step["type"] == "done":
                return self._success(
                    step.get("summary", "Objective completed."),
                    raw=self.observations[-1]["result"]
                    if self.observations else None,
                )

            if step["type"] == "tool":
                self._execute_tool(step, resolved_id)

                if terminal:
                    last = self.observations[-1]
                    return self._success(
                        summary="Action completed successfully.",
                        raw=last["result"],
                    )

    # --------------------------------------------------
    # Run-local state
    # --------------------------------------------------
    def _reset_run_state(self) -> None:
        self.observations: List[Dict[str, Any]] = []
        self.called_tools: set[str] = set()

    # --------------------------------------------------
    # 🔒 CREATE tool selector (FIXED)
    # --------------------------------------------------
    def _select_create_tool(self, objective: Dict[str, Any]):
        for name in self.tools.list():
            tool = self.tools.get(name)
            caps = getattr(tool, "capabilities", {})

            if (
                caps.get("domain") == objective.get("domain")
                and caps.get("intent") == objective.get("intent")
            ):
                return tool

        raise ValueError(
            f"No CREATE tool registered for "
            f"{objective.get('domain')}::{objective.get('intent')}"
        )

    # --------------------------------------------------
    # Candidate retrieval (DISCOVERY ROUTING)
    # --------------------------------------------------
    def _retrieve_candidates(self, objective: Dict[str, Any]) -> List[Dict[str, Any]]:
        constraints = objective.get("constraints") or {}
        limit = constraints.get("limit", 10)
        discovery_scope = constraints.get("discovery_scope", "unread_only")

        tool_name = (
            "list_recent_emails"
            if discovery_scope == "recent_any"
            else "check_unread"
        )

        tool = self.tools.get(tool_name)

        log.warning(
            "NEMESIS DISCOVERY | scope=%s | tool=%s | limit=%d",
            discovery_scope,
            tool_name,
            limit,
        )

        raw_result = tool.run({"limit": limit})

        messages = (
            raw_result
            if isinstance(raw_result, list)
            else raw_result.get("messages", [])
        )

        return [email_to_candidate(m) for m in messages]

    # --------------------------------------------------
    # LLM decision
    # --------------------------------------------------
    def _decide_next_step(self, objective: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._build_prompt(objective)
        response = self.llm.invoke(prompt)
        return self._parse_llm_step(response.content)

    # --------------------------------------------------
    # Tool execution (STRICT)
    # --------------------------------------------------
    def _execute_tool(self, step: Dict[str, Any], resolved_id: str | None) -> None:
        tool_name = step["tool"]
        llm_args = step.get("args", {})

        if tool_name in self.called_tools:
            raise ValueError(f"Repeated tool call blocked: {tool_name}")

        tool = self.tools.get(tool_name)

        args = dict(llm_args)
        if resolved_id and "id" not in args:
            args["id"] = resolved_id

        self.tools.validate_args(tool_name, args)

        log.warning(
            "NEMESIS TOOL CALL | tool=%s | args=%r",
            tool_name,
            args,
        )

        result = tool.run(args)

        self.called_tools.add(tool_name)
        self.observations.append({
            "tool": tool_name,
            "args": args,
            "result": result,
        })

    # --------------------------------------------------
    # Prompting
    # --------------------------------------------------
    def _build_prompt(self, objective: Dict[str, Any]) -> str:
        return f"""
You are NEMESIS, an execution-only agent.

Objective (READ-ONLY):
{json.dumps(objective, indent=2)}

Available tools:
{self.tools.describe()}

Observations:
{json.dumps(self.observations, indent=2)}

Rules:
- Choose exactly ONE action
- Either call ONE tool or return DONE
- Never repeat a tool
- Never ask questions
- Never invent IDs
- Output JSON only
"""

    # --------------------------------------------------
    # Parsing
    # --------------------------------------------------
    def _parse_llm_step(self, content: str) -> Dict[str, Any]:
        raw = json.loads(content)

        if raw.get("type") == "done":
            return {"type": "done", "summary": raw.get("summary")}

        tool = raw.get("tool") or raw.get("action")
        if tool:
            return {"type": "tool", "tool": tool, "args": raw.get("args", {})}

        raise ValueError(f"Invalid step: {raw}")

    # --------------------------------------------------
    # Validation & result
    # --------------------------------------------------
    def _validate_state(self, state: Dict[str, Any]) -> None:
        if not state.get("objective"):
            raise ValueError("NEMESIS requires an objective")

    def _success(self, summary: str, raw: Any = None) -> Dict[str, Any]:
        return {
            "status": "success",
            "summary": summary,
            "artifacts": {"raw_data": raw} if raw is not None else {},
        }
