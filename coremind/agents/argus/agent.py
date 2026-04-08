import json
from typing import Dict, Any

from coremind.llms.factory import LLMFactory
from coremind.logging import get_logger
from .prompt import ARGUS_SYSTEM_PROMPT

log = get_logger("ARGUS")


class ArgusAgent:
    """
    Constitutional governance agent.
    Performs high-trust validation before execution.
    """

    def __init__(self):
        self.llm = LLMFactory.argus()

    def evaluate(
        self,
        objective: Dict[str, Any],
        state: Dict[str, Any],
    ) -> Dict[str, Any]:

        log.info("ARGUS evaluating objective: %s", objective)

        user_prompt = f"""
Evaluate the following proposed action.

Objective:
{json.dumps(objective, indent=2)}

System State:
{json.dumps(state, indent=2)}

Remember:
- Be strict.
- If information is missing, reject.
- If identity is ambiguous, reject.
- If irreversible financial action, escalate.
- Return JSON only.
"""

        response = self.llm.invoke(
            [
                {"role": "system", "content": ARGUS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )

        content = response.content.strip()

        try:
            parsed = json.loads(content)

            # Fail-safe validation
            required_keys = {
                "approved",
                "risk_level",
                "violations",
                "reasoning",
                "confidence",
            }

            if not required_keys.issubset(parsed.keys()):
                raise ValueError("Missing required keys")

            return parsed

        except Exception as e:
            log.error("ARGUS failed to parse response: %s", e)
            log.error("Raw response: %s", content)

            # FAIL CLOSED
            return {
                "approved": False,
                "risk_level": "critical",
                "violations": ["Invalid ARGUS response format"],
                "reasoning": "ARGUS response could not be parsed.",
                "confidence": 0.0,
            }

    def _review_with_argus(self, task: str, plan: Dict, result: Dict) -> Dict:
        prompt = f"""
    You are ARGUS, a strict code reviewer.

    Task:
    {task}

    Proposed action:
    {plan}

    Result:
    {result}

    Evaluate:
    - Is the fix correct?
    - Any bugs or edge cases?
    - Will it break anything?

    Return JSON:
    {{
    "status": "approved" | "rejected",
    "reason": "explanation",
    "improvement": "suggested fix if rejected"
    }}
    """

        response = self.reviewer.invoke(prompt)
        return self._safe_parse(response)