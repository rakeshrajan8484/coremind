from typing import Dict, Any, List
import json

from langchain_core.messages import SystemMessage, HumanMessage

from coremind.llms.factory import LLMFactory
from coremind.logging import get_logger

from coremind.agents.nexis.planners.plan import create_plan
from coremind.agents.nexis.context.builder import build_context

from coremind.agents.nexis.tools.file_ops import write_file, read_file

from coremind.agents.nexis.prompt import NEXIS_SYSTEM_PROMPT


# -------------------------------------------------
# 🔒 Helpers
# -------------------------------------------------

def is_tool_response(text: str) -> bool:
    """
    Detect if LLM returned tool JSON instead of code.
    """
    try:
        data = json.loads(text)
        return isinstance(data, dict) and "action" in data
    except Exception:
        return False


def validate_path(path: str):
    if not path or "." not in path:
        raise ValueError(f"Invalid file path: {path}")


# -------------------------------------------------
# 🧠 NEXIS NODE
# -------------------------------------------------

def make_nexis_node():
    llm = LLMFactory.nexis()

    def nexis_node(state: Dict[str, Any]) -> Dict[str, Any]:
        log = get_logger("NEXIS")
        log.info("=== ENTER NEXIS NODE ===")

        obj = state.get("objective")
        root = state.get("root_path")

        # -------------------------
        # Validate inputs
        # -------------------------
        if not obj:
            log.warning("No objective found")
            return state

        if not root:
            return {
                **state,
                "result": {
                    "status": "error",
                    "message": "root_path is required for code execution"
                }
            }

        operation_type = obj.get("operation", {}).get("type")

        try:
            # -------------------------
            # PLAN
            # -------------------------
            plan = create_plan(obj)
            log.info(f"PLAN: {plan}")

            # -------------------------
            # PREPARE MODIFY CONTEXT
            # -------------------------
            if plan.get("type") == "file_modification":
                for file_plan in plan["files"]:
                    path = file_plan.get("path")
                    validate_path(path)

                    # Read existing file
                    existing_code = read_file(root, path)
                    file_plan["existing_code"] = existing_code

            # -------------------------
            # BUILD CONTEXT
            # -------------------------
            contexts = build_context(obj, plan)

            created_files: List[str] = []

            # -------------------------
            # EXECUTION LOOP
            # -------------------------
            for ctx in contexts:
                path = ctx["path"]
                prompt = ctx["prompt"]

                validate_path(path)

                log.info(f"Processing file: {path}")

                # -------------------------
                # LLM CALL
                # -------------------------
                response = llm.invoke([
                    SystemMessage(content=NEXIS_SYSTEM_PROMPT),
                    HumanMessage(content=prompt)
                ])

                code = response.content.strip()

                # -------------------------
                # GUARD: prevent tool JSON
                # -------------------------
                if is_tool_response(code):
                    raise Exception("LLM returned tool call instead of code")

                # -------------------------
                # WRITE FILE
                # -------------------------
                full_path = write_file(root, path, code)
                created_files.append(full_path)

                log.info(f"File written: {full_path}")

            # -------------------------
            # RETURN RESULT
            # -------------------------
            return {
                **state,
                "result": {
                    "status": "success",
                    "artifacts": {
                        "files": created_files,
                        "plan": plan,
                        "operation": operation_type
                    }
                }
            }

        except Exception as e:
            log.exception("NEXIS execution failed")

            return {
                **state,
                "result": {
                    "status": "error",
                    "message": str(e),
                    "operation": operation_type
                }
            }

    return nexis_node

