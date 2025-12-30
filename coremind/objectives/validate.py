# coremind/objectives/validate.py

from typing import Dict, Any
from .registry import OBJECTIVE_REGISTRY


def validate_objective(objective: Dict[str, Any]) -> bool:
    """
    Validate an objective against its ObjectiveSpec.

    IMPORTANT CONTRACT:
    - This function validates STRUCTURE + SPEC CONFORMANCE
    - It MUST support read-only intents like `summarize`
    - It MUST NOT assume update-only semantics
    """

    if not isinstance(objective, dict):
        return False

    # -------------------------------------------------
    # 1️⃣ Resolve spec
    # -------------------------------------------------
    domain = objective.get("domain")
    intent = objective.get("intent")

    if not domain or not intent:
        return False

    key = (domain, intent)
    spec = OBJECTIVE_REGISTRY.get(key)

    if not spec:
        return False

    # -------------------------------------------------
    # 2️⃣ Target validation
    # -------------------------------------------------
    target = objective.get("target")
    if not isinstance(target, dict):
        return False

    selector = target.get("selector")
    filters = target.get("filter")

    if selector not in spec.allowed_selectors:
        return False

    if filters is None or not isinstance(filters, dict):
        return False

    # Required filter fields ONLY if spec demands them
    required_fields = spec.required_filter_fields.get(selector, [])
    for field in required_fields:
        if field not in filters:
            return False

    # -------------------------------------------------
    # 3️⃣ Operation validation
    # -------------------------------------------------
    operation = objective.get("operation")
    if not isinstance(operation, dict):
        return False

    op_type = operation.get("type")
    op_value = operation.get("value")

    if not op_type or not op_value:
        return False

    # STRICT spec match
    if op_type != spec.operation_type:
        return False

    if op_value not in spec.allowed_operation_values:
        return False

    # -------------------------------------------------
    # 4️⃣ Constraints (optional, opaque)
    # -------------------------------------------------
    constraints = objective.get("constraints")
    if constraints is not None and not isinstance(constraints, dict):
        return False

    # -------------------------------------------------
    # ✅ Objective is VALID
    # -------------------------------------------------
    return True
