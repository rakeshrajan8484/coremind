from typing import Dict, Any, List
from coremind.llms.factory import LLMFactory

from .tools.file_ops import read_file, write_file
from .tools.exec import run_python


class NexisAgent:
    """
    NEXIS: Code execution + debugging agent
    """

    def __init__(self, root_path: str, llm: BaseChatModel):
        self.root_path = root_path
        self.llm = LLMFactory.nexis()
        self.reviewer = LLMFactory.argus()
        self.max_iterations = 5

    # ------------------------------
    # Public Entry
    # ------------------------------
    def execute(self, task: str) -> Dict[str, Any]:
        """
        Main entry point for NEXIS
        """
        context = self._build_context(task)

        history: List[Dict[str, Any]] = []

        for step in range(self.max_iterations):
            plan = self._plan(task, context, history)

            action_result = self._act(plan)

            # 🔍 ARGUS REVIEW STEP
            review = self._review_with_argus(task, plan, action_result)

            if review.get("status") == "rejected":
                fix = self._refine_from_review(task, review)
                self._apply_fix(fix)
                continue

            history.append({
                "step": step,
                "plan": plan,
                "result": action_result,
                "review": review,
            })

            # ✅ success
            if action_result.get("status") == "success":
                return {
                    "status": "success",
                    "steps": history,
                    "message": action_result.get("message"),
                }

            # ❌ error → fix
            if action_result.get("status") == "error":
                fix = self._fix_error(task, action_result, context)
                self._apply_fix(fix)

        return {
            "status": "failed",
            "steps": history,
            "message": "Max iterations reached without success",
        }

    # ------------------------------
    # Context Builder
    # ------------------------------
    def _build_context(self, task: str) -> Dict[str, Any]:
        """
        Minimal context (can upgrade later with semantic search)
        """
        return {
            "task": task,
            "files": [],  # extend later
        }

    # ------------------------------
    # Planning Step (LLM)
    # ------------------------------
    def _plan(self, task: str, context: Dict, history: List) -> Dict:
        prompt = f"""
You are NEXIS, a coding agent.

Task:
{task}

Previous attempts:
{history}

Return a JSON plan:
{{
  "action": "read_file | write_file | run_code",
  "target": "file path",
  "content": "code if needed",
  "reason": "why"
}}
"""

        response = self.llm.invoke(prompt)

        return self._safe_parse(response)

    # ------------------------------
    # Action Execution
    # ------------------------------
    def _act(self, plan: Dict) -> Dict:
        try:
            action = plan.get("action")

            if action == "read_file":
                content = read_file(plan["target"])
                return {"status": "success", "content": content}

            elif action == "write_file":
                write_file(plan["target"], plan.get("content", ""))
                return {"status": "success", "message": "File written"}

            elif action == "run_code":
                result = run_python(plan["target"])

                if result.returncode == 0:
                    return {
                        "status": "success",
                        "message": result.stdout,
                    }
                else:
                    return {
                        "status": "error",
                        "error": result.stderr,
                    }

            return {"status": "error", "error": "Unknown action"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ------------------------------
    # Error Fixing (LLM)
    # ------------------------------
    def _fix_error(self, task: str, error_result: Dict, context: Dict) -> Dict:
        prompt = f"""
You are NEXIS fixing a bug.

Task:
{task}

Error:
{error_result.get("error")}

Return JSON:
{{
  "target": "file to fix",
  "fixed_code": "updated code"
}}
"""

        response = self.llm.invoke(prompt)

        return self._safe_parse(response)

    # ------------------------------
    # Apply Fix
    # ------------------------------
    def _apply_fix(self, fix: Dict):
        target = fix.get("target")
        code = fix.get("fixed_code")

        if target and code:
            write_file(target, code)

    # ------------------------------
    # Utils
    # ------------------------------
    def _safe_parse(self, response) -> Dict:
        """
        Basic JSON parser with fallback
        """
        try:
            import json

            if hasattr(response, "content"):
                return json.loads(response.content)

            return json.loads(response)

        except Exception:
            return {
                "action": "none",
                "reason": "Failed to parse LLM response",
            }

    def _refine_from_review(self, task: str, review: Dict) -> Dict:
        prompt = f"""
    You are NEXIS improving code based on review.

    Task:
    {task}

    Reviewer feedback:
    {review.get("reason")}
    {review.get("improvement")}

    Return JSON:
    {{
    "target": "file to update",
    "fixed_code": "improved code"
    }}
    """

        response = self.llm.invoke(prompt)
        return self._safe_parse(response)