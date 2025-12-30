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

    # --------------------------------------------------
    # Public entry
    # --------------------------------------------------

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        self._reset_run_state()
        self._validate_state(state)

        objective = state["objective"]

        # --------------------------------------------------
        # 🔒 CANONICAL ID NORMALIZATION (ONCE)
        # --------------------------------------------------
        resolved_id = state.get("resolved_id")
        if not resolved_id:
            resolved_id = (
                objective
                .get("target", {})
                .get("filter", {})
                .get("id")
            )

        domain = objective.get("domain")
        intent = objective.get("intent")
        terminal = (domain, intent) in TERMINAL_INTENTS

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
        # 🔒 HARD CONTRACT: resolved identity required
        # --------------------------------------------------
        target = objective.get("target", {})
        if target.get("selector") == "single" and not resolved_id:
            raise ValueError(
                "NEMESIS cannot execute objective requiring identity "
                "without a concrete ID"
            )

        # --------------------------------------------------
        # Normal execution loop
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
    # Candidate retrieval (DISCOVERY ROUTING)
    # --------------------------------------------------

    def _retrieve_candidates(self, objective: Dict[str, Any]) -> List[Dict[str, Any]]:
        constraints = objective.get("constraints") or {}
        limit = constraints.get("limit", 10)

        discovery_scope = constraints.get("discovery_scope", "unread_only")

        if discovery_scope == "recent_any":
            tool_name = "list_recent_emails"
        else:
            tool_name = "check_unread"

        tool = self.tools.get(tool_name)
        if not tool:
            raise ValueError(f"Discovery tool not available: {tool_name}")

        log.warning(
            "NEMESIS DISCOVERY | scope=%s | tool=%s | limit=%d",
            discovery_scope,
            tool_name,
            limit,
        )

        raw_result = tool.run({"limit": limit})

        if isinstance(raw_result, list):
            messages = raw_result
        elif isinstance(raw_result, dict):
            messages = raw_result.get("messages", [])
        else:
            raise ValueError(f"Unsupported retrieval result: {type(raw_result)}")

        entity = objective.get("target", {}).get("entity")
        if entity != "message":
            raise ValueError(f"No adapter for entity type: {entity}")

        candidates = [email_to_candidate(m) for m in messages]
        log.debug("Candidates sample: %s", candidates[:2])
        return candidates

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
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")

        args = dict(llm_args)
        if resolved_id and "id" not in args:
            args["id"] = resolved_id

        schema = tool.args_schema or {}

        for arg, spec in schema.items():
            if spec.get("required") and arg not in args:
                raise ValueError(
                    f"Tool '{tool_name}' missing required arg: '{arg}'"
                )

        for arg in args:
            if arg not in schema:
                raise ValueError(
                    f"Tool '{tool_name}' received unknown arg: '{arg}'"
                )

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
        try:
            raw = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from NEMESIS:\n{content}") from e

        if not isinstance(raw, dict):
            raise ValueError("Step must be a JSON object")

        step_type = raw.get("type")

        if step_type == "done":
            return {
                "type": "done",
                "summary": raw.get("summary"),
            }

        tool_name = (
            raw.get("tool")
            or raw.get("action")
            or raw.get("tool_name")
        )

        if tool_name:
            return {
                "type": "tool",
                "tool": tool_name,
                "args": raw.get("args", {}),
            }

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
