from typing import Dict, Any, List


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def build_base_instruction(file_type: str) -> str:
        return f"Generate {file_type} code"


def build_rules() -> str:
    return (
        "Rules:\n"
        "- Return ONLY raw code\n"
        "- Do NOT return JSON\n"
        "- Do NOT describe actions\n"
        "- Do NOT include explanations\n"
        "- Do NOT wrap in markdown\n"
        "- Output must be directly writable to a file\n"
    )


def build_constraints(constraints: Dict[str, Any]) -> str:
    if not constraints:
        return ""

    lines = ["Constraints:"]
    for k, v in constraints.items():
        if v:
            lines.append(f"- {k}: {v}")

    return "\n".join(lines)


# --------------------------------------------------
# Per-file context builder
# --------------------------------------------------

def build_file_prompt(objective: Dict[str, Any], file_plan: Dict[str, Any]) -> str:
    intent_text = objective.get("intent_text", "")
    constraints = objective.get("constraints", {})
    file_type = file_plan.get("type")
    path = file_plan.get("path")
    purpose = file_plan.get("purpose", "")
    existing_code = file_plan.get("existing_code", "")
    operation = file_plan.get("operation")
    instruction = file_plan.get("instruction")
    rules = build_rules()
    constraint_text = build_constraints(constraints)
    if operation == "modify":
        return f"""
    You are a senior software engineer.

    Modify the following code based on the instruction.

    Instruction:
    {instruction}

    Existing Code:
    {existing_code}

    Rules:
    - Return full updated code
    - Do not remove unrelated parts
    - Do not explain
    - Do not return partial code
    """
    return f"""
You are a senior software engineer.

Task:
{intent_text}

File:
- Path: {path}
- Type: {file_type}
- Purpose: {purpose}

Instructions:
{instruction}

{constraint_text}

{rules}
""".strip()


# --------------------------------------------------
# Main builder
# --------------------------------------------------

def build_context(objective: Dict[str, Any], plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not objective:
        raise ValueError("Objective is required")

    if not plan:
        raise ValueError("Plan is required")

    files = plan.get("files", [])
    if not files:
        raise ValueError("Plan contains no files")

    contexts: List[Dict[str, Any]] = []

    for file_plan in files:
        prompt = build_file_prompt(objective, file_plan)

        contexts.append({
            "path": file_plan.get("path"),
            "type": file_plan.get("type"),
            "prompt": prompt
        })

    return contexts

