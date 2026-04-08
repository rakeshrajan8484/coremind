from typing import Dict, Any, List


# --------------------------------------------------
# File type inference
# --------------------------------------------------

def infer_file_type(intent_text: str, constraints: Dict[str, Any]) -> str:
    text = (intent_text or "").lower()
    description = (constraints.get("description") or "").lower()

    combined = f"{text} {description}"

    if "html" in combined:
        return "html"
    if "css" in combined:
        return "css"
    if "javascript" in combined or "js" in combined:
        return "js"
    if "python" in combined:
        return "py"

    # default fallback
    return "txt"


# --------------------------------------------------
# Path normalization
# --------------------------------------------------

def normalize_path(constraints: Dict[str, Any], file_type: str) -> str:
    path = constraints.get("path")

    if path:
        return path

    # default naming
    if file_type == "html":
        return "index.html"
    if file_type == "css":
        return "styles.css"
    if file_type == "js":
        return "script.js"
    if file_type == "py":
        return "main.py"

    return "output.txt"


# --------------------------------------------------
# Plan builders
# --------------------------------------------------

def build_single_file_plan(objective: Dict[str, Any]) -> Dict[str, Any]:
    constraints = objective.get("constraints", {})
    intent_text = objective.get("intent_text", "")

    file_type = infer_file_type(intent_text, constraints)
    path = normalize_path(constraints, file_type)

    return {
        "type": "file_generation",
        "mode": "single",
        "files": [
            {
                "path": path,
                "type": file_type,
                "purpose": constraints.get("description") or intent_text
            }
        ]
    }



def build_modify_plan(objective: Dict[str, Any]) -> Dict[str, Any]:
    target = objective.get("target", {})
    constraints = objective.get("constraints") or {}

    # ⚠️ You NEED a path here
    path = constraints.get("path") or target.get("path")

    if not path:
        raise ValueError("modify_code requires a file path")

    return {
        "type": "file_modification",
        "mode": "single",
        "files": [
            {
                "path": path,
                "type": "unknown",  # inferred later if needed
                "operation": "modify",
                "instruction": objective.get("intent_text")
            }
        ]
    }


def build_multi_file_plan(objective: Dict[str, Any]) -> Dict[str, Any]:
    """
    Future: React apps, full-stack scaffolding, etc.
    """
    constraints = objective.get("constraints", {})
    intent_text = objective.get("intent_text", "").lower()

    files: List[Dict[str, Any]] = []

    # Example: simple web app
    if "web" in intent_text or "website" in intent_text:
        files = [
            {"path": "index.html", "type": "html"},
            {"path": "styles.css", "type": "css"},
            {"path": "script.js", "type": "js"},
        ]

    if not files:
        return build_single_file_plan(objective)

    return {
        "type": "file_generation",
        "mode": "multi",
        "files": files
    }


# --------------------------------------------------
# Main planner entry
# --------------------------------------------------

def create_plan(objective: Dict[str, Any]) -> Dict[str, Any]:
    if not objective:
        raise ValueError("Objective is required")

    domain = objective.get("domain")
    intent = objective.get("intent")

    if intent == "modify_code":
        return build_modify_plan(objective)

    if domain != "code":
        raise ValueError(f"Planner does not support domain: {domain}")

    if intent != "generate_code":
        raise ValueError(f"Unsupported intent: {intent}")

    intent_text = objective.get("intent_text", "").lower()

    # Decide plan type
    if any(word in intent_text for word in ["app", "project", "website"]):
        return build_multi_file_plan(objective)

    return build_single_file_plan(objective)

