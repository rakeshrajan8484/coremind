from typing import Dict, Any, List
import json

from coremind.agents.nemesis.adapters.email import email_to_candidate
from coremind.llms.factory import LLMFactory
import coremind.agents.nemesis.tools  # force tool registration
from coremind.agents.nemesis.tools.registry import TOOL_REGISTRY
from coremind.logging import get_logger

log = get_logger("NEMESIS")


TERMINAL_INTENTS = {
    ("email", "update_read_state"),
    ("email", "update_bulk_read_state"),
    ("email", "delete_message"),
    ("email", "summarize"),
    ("email", "compose_message"),
    ("email", "send_draft"),
    ("email", "count"),
}


class NemesisAgent:
    """
    Execution-only agent.

    CONTRACT:
    - No planning
    - No reference resolution
    - No user-facing language
    - Deterministic execution only
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

        self.state = state
        self.current_objective = state["objective"]

        objective = self.current_objective
        domain = objective.get("domain")
        intent = objective.get("intent")

        resolved_id = self._extract_concrete_id(objective, state)

        # --------------------------------------------------
        # HARD TERMINALS (NO LLM)
        # --------------------------------------------------
        if (domain, intent) == ("smart_home", "switch_power"):
            tool = self.tools.get("smart_home_control")

            if not tool:
                raise RuntimeError(f"No tool registered for intent: {intent}")

            # 1. Build args from constraints
            constraints = objective.get("constraints")
            if not isinstance(constraints, dict):
                raise ValueError("SMART_HOME constraints must be a dict")

            args = dict(constraints)

            # 2. Merge allowed target.filter fields
            target_filter = objective.get("target", {}).get("filter", {}) or {}
            allowed_args = set(tool.args_schema.keys())

            for k, v in target_filter.items():
                if k in allowed_args:
                    args.setdefault(k, v)

            # 3. Enforce semantic completeness
            if args.get("action") not in {"switch_on", "switch_off", "toggle"}:
                raise ValueError(f"Invalid smart_home action: {args.get('action')}")

            # 4. Validate args
            self.tools.validate_args(tool.name, args)

            # 5. Enforce terminal invariant
            if tool.terminal is not True:
                raise RuntimeError("SmartHomeControlTool must be terminal")

            log.warning(
                "NEMESIS TOOL CALL | tool=%s | args=%r",
                tool.name,
                args,
            )

            result = tool.run(args)

            return {
                "status": "success",
                "artifacts": {
                    "raw_data": result,
                    "force_done": bool(result.get("terminal", False)),
                },
            }


        if (domain, intent) == ("entity", "retrieve_candidates"):
            candidates = self._retrieve_candidates(objective)
            return {
                "status": "success",
                "artifacts": {"candidates": candidates},
            }

        if objective.get("operation", {}).get("type") == "create":
            tool = self.tools.get(objective["intent"])

            if not tool:
                raise RuntimeError(
                    f"No tool registered for intent: {objective['intent']}"
                )

            # ----------------------------
            # 1. Build args from constraints
            # ----------------------------
            constraints = objective.get("constraints")
            if isinstance(constraints, dict):
                args = dict(constraints)
            else:
                raise ValueError("CREATE constraints must be a dict")

            # ----------------------------
            # 2. Merge ONLY allowed target.filter fields
            # ----------------------------
            target_filter = objective.get("target", {}).get("filter", {}) or {}

            allowed_args = set(tool.args_schema.keys())

            for k, v in target_filter.items():
                if k in allowed_args:
                    args.setdefault(k, v)

            # ----------------------------
            # 3. Validate & execute
            # ----------------------------
            self.tools.validate_args(tool.name, args)

            log.warning(
                "NEMESIS TOOL CALL | tool=%s | args=%r",
                tool.name,
                args,
            )

            result = tool.run(args)

            return {
                "status": "success",
                "artifacts": {"raw_data": result},
            }

            # 🔒 merge target.filter (execution wiring, not logic)
            target_filter = objective.get("target", {}).get("filter", {}) or {}
            for k, v in target_filter.items():
                args.setdefault(k, v)

            self.tools.validate_args(tool.name, args)

            log.warning("NEMESIS TOOL CALL | tool=%s | args=%r", tool.name, args)
            result = tool.run(args)

            return {
                "status": "success",
                "artifacts": {"raw_data": result},
            }


        if (domain, intent) == ("email", "send_draft"):
             
            tool = self.tools.get("send_draft")
            args = {"id": resolved_id}
            self.tools.validate_args("send_draft", args)

            log.warning("NEMESIS TOOL CALL | tool=send_draft | args=%r", args)
            result = tool.run(args)

            return {
                "status": "success",
                "artifacts": {"raw_data": result},
            }

        terminal = (domain, intent) in TERMINAL_INTENTS

        # --------------------------------------------------
        # MAIN EXECUTION LOOP
        # --------------------------------------------------
        while True:
            step = self._decide_next_step(objective)

            # Normalize the LLM-chosen step to prefer deterministic bulk tools
            # when the objective already contains multiple ids or a sender filter.
            if step.get("type") == "tool":
                step = self._normalize_tool_choice(step, objective)

            if step["type"] == "done":
                return {
                    "status": "success",
                    "artifacts": {},
                }

            if step["type"] == "tool":
                result = self._execute_tool(step, resolved_id)

                # 🔒 HARD TERMINATION (destructive tools)
                if isinstance(result, dict):
                    artifacts = result.get("artifacts") or {}
                    if artifacts.get("force_done"):
                        return {
                            "status": "success",
                            "artifacts": {"raw_data": result},
                        }

                if terminal:
                    last = self.observations[-1]
                    return {
                        "status": "success",
                        "artifacts": {"raw_data": last["result"]},
                    }

    # --------------------------------------------------
    # Tool execution (STRICT)
    # --------------------------------------------------
    def _execute_tool(self, step: Dict[str, Any], resolved_id: str | None):
        tool_name = step["tool"]
        llm_args = step.get("arguments") or step.get("args") or {}

        if tool_name in self.called_tools:
            raise ValueError(f"Repeated tool call blocked: {tool_name}")

        tool = self.tools.get(tool_name)

        resolved_args = self._resolve_tool_args(
            tool_name=tool_name,
            step_args=llm_args,
            objective=self.current_objective,
            state=self.state,
            resolved_id=resolved_id,
        )

        self.tools.validate_args(tool_name, resolved_args)

        log.warning(
            "NEMESIS TOOL CALL | tool=%s | args=%r",
            tool_name,
            resolved_args,
        )

        result = tool.run(resolved_args)

        # Ensure count results are wrapped for ATLAS summary
        if self.current_objective.get("intent") == "count" and isinstance(result, list):
            result = {"count": len(result)}

        self.called_tools.add(tool_name)
        self.observations.append({
            "tool": tool_name,
            "args": resolved_args,
            "result": result,
        })

        return result

    # --------------------------------------------------
    # Argument resolution (CORE INVARIANT)
    # --------------------------------------------------
    def _resolve_tool_args(
        self,
        tool_name: str,
        step_args: dict,
        objective: dict,
        state: dict,
        resolved_id: str | None,
    ) -> dict:

        args = dict(step_args or {})
        target = objective.get("target", {}) or {}
        filter_ = target.get("filter", {}) or {}

        if tool_name == "delete_emails_bulk":
            if "sender" not in args and filter_.get("sender"):
                args["sender"] = filter_["sender"]

            if "ids" not in args:
                ids = filter_.get("ids")
                if isinstance(ids, list) and ids:
                    args["ids"] = ids
                elif resolved_id:
                    args["ids"] = [resolved_id]

            if not any(k in args for k in ("sender", "ids")):
                raise RuntimeError(
                    "Execution invariant violated: bulk delete without identity"
                )

        if tool_name == "mark_all_read":
            # If caller provided some ids, merge them with objective filter ids so
            # we don't lose targets (LLM may supply a single id while objective
            # contains multiple resolved ids).
            ids_in_args = args.get("ids")
            filter_ids = filter_.get("ids")

            if ids_in_args and isinstance(ids_in_args, list) and filter_ids and isinstance(filter_ids, list):
                # merge preserving order, unique
                merged = []
                for x in ids_in_args + filter_ids:
                    if x and x not in merged:
                        merged.append(x)
                args["ids"] = merged
            elif "ids" not in args:
                if isinstance(filter_ids, list) and filter_ids:
                    args["ids"] = filter_ids

            # If sender provided in objective filter and not in args, pass it through
            if "sender" not in args and filter_.get("sender"):
                args["sender"] = filter_["sender"]

            # If we still have no ids or sender, fall back to a limit (handled by tool)
            # Remove any unknown keys that the tool does not accept (defensive).
            try:
                tool = self.tools.get("mark_all_read")
                allowed = set(tool.args_schema.keys())
                # keep only allowed args
                args = {k: v for k, v in args.items() if k in allowed}
            except Exception:
                # if tool not registered or schema missing, leave args as-is
                pass

        if tool_name in {"delete_email", "mark_email", "get_email_content"}:
            if "id" not in args:
                ids = filter_.get("ids")
                id_from_filter = ids[0] if isinstance(ids, list) and ids else None
                msg_id = filter_.get("id") or id_from_filter or resolved_id
                if msg_id:
                    args["id"] = msg_id

        return args

    # --------------------------------------------------
    # Utilities
    # --------------------------------------------------
    def _extract_concrete_id(self, objective, state):
        if state.get("resolved_id"):
            return state["resolved_id"]

        target = objective.get("target") or {}
        filter_ = target.get("filter") or {}
        ids = filter_.get("ids")
        id_from_ids = ids[0] if isinstance(ids, list) and ids else None

        return (
            filter_.get("id")
            or id_from_ids
            or filter_.get("draft_id")
            or filter_.get("thread_id")
        )

    def _reset_run_state(self):
        self.observations: List[Dict[str, Any]] = []
        self.called_tools: set[str] = set()

    def _decide_next_step(self, objective):
        prompt = self._build_prompt(objective)
        response = self.llm.invoke(prompt)
        return self._parse_llm_step(response.content)

    def _build_prompt(self, objective):
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
- Never invent IDs
- Output JSON only
"""

    # --------------------------------------------------
    # Parsing (LLM-HARDENED)
    # --------------------------------------------------
    def _parse_llm_step(self, content: str) -> Dict[str, Any]:
        if not content or not content.strip():
            raise ValueError("LLM returned empty response")

        text = content.strip()
        first_open = text.find("{")
        if first_open == -1:
            raise ValueError(f"LLM returned no JSON:\n{text}")

        brace_count = 0
        json_end = None
        for i in range(first_open, len(text)):
            if text[i] == "{":
                brace_count += 1
            elif text[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    json_end = i
                    break

        if json_end is None:
            raise ValueError(f"Unclosed JSON object:\n{text}")

        raw = json.loads(text[first_open:json_end + 1])

        if raw.get("type") == "done":
            return {"type": "done"}

        if "name" in raw or "tool" in raw:
            return {
                "type": "tool",
                "tool": raw.get("name") or raw.get("tool"),
                "arguments": raw.get("args", {}),
            }

        # HF fallback: echoed objective
        if (
            "domain" in raw
            and "intent" in raw
            and "target" in raw
            and "operation" in raw
        ):
            return {
                "type": "tool",
                "tool": self._tool_from_objective(raw),
                "arguments": {},
            }

        raise ValueError(f"Invalid LLM step JSON:\n{raw}")

    def _tool_from_objective(self, objective: Dict[str, Any]) -> str:
        domain = objective.get("domain")
        intent = objective.get("intent")

        if (domain, intent) == ("email", "delete_messages_bulk"):
            return "delete_emails_bulk"
        if (domain, intent) == ("email", "delete_message"):
            return "delete_email"
        if (domain, intent) == ("email", "update_read_state"):
            # Prefer bulk mark tool if multiple ids or sender filter provided.
            filter_ = objective.get("target", {}).get("filter", {}) or {}
            if isinstance(filter_.get("ids"), list) and filter_["ids"]:
                return "mark_all_read"
            if filter_.get("sender") or filter_.get("from"):
                return "mark_all_read"
            return "mark_email"

        raise ValueError(f"No tool mapping for {domain}::{intent}")

    def _normalize_tool_choice(self, step: Dict[str, Any], objective: Dict[str, Any]) -> Dict[str, Any]:
        """If the LLM selected a single-item tool but the objective clearly
        targets multiple messages (ids list or sender), prefer the bulk tool.
        This enforces the contract that bulk operations are performed
        deterministically when concrete ids are already available.
        """
        tool = step.get("tool")
        if not tool:
            return step

        filter_ = objective.get("target", {}).get("filter", {}) or {}

        if tool == "mark_email":
            if isinstance(filter_.get("ids"), list) and filter_["ids"]:
                step["tool"] = "mark_all_read"
            elif filter_.get("sender") or filter_.get("from"):
                step["tool"] = "mark_all_read"

            # If the LLM provided a single 'id' argument, migrate it to 'ids'
            # so the bulk tool receives the correct param name and passes schema validation.
            args = step.get("arguments") or step.get("args") or {}
            if step.get("tool") == "mark_all_read" and "id" in args:
                args.setdefault("ids", [args.pop("id")])
                step["arguments"] = args

        if tool == "delete_email":
            if isinstance(filter_.get("ids"), list) and len(filter_["ids"]) > 1:
                step["tool"] = "delete_emails_bulk"
            elif filter_.get("sender") or filter_.get("from"):
                step["tool"] = "delete_emails_bulk"

            # Migrate 'id' -> 'ids' if switched to bulk
            args = step.get("arguments") or step.get("args") or {}
            if step.get("tool") == "delete_emails_bulk" and "id" in args:
                args.setdefault("ids", [args.pop("id")])
                step["arguments"] = args

        return step

    def _retrieve_candidates(self, objective):
        tool = self.tools.get("list_recent_emails")
        # 🔒 Pass target filters to enable pre-filtering of both read/unread emails
        raw = tool.run({
            "limit": 10,
            "target": objective.get("target", {})
        })
        return [email_to_candidate(m) for m in raw]

    def _validate_state(self, state):
        if not state.get("objective"):
            raise ValueError("NEMESIS requires an objective")
