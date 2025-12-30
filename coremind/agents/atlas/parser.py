# coremind/agents/atlas/parser.py

import json

REQUIRED_KEYS = {
    "domain",
    "intent",
    "target",
    "operation",
    "constraints",
}


def validate_objective(objective: dict) -> bool:
    key = (objective["domain"], objective["intent"])
    spec = OBJECTIVE_REGISTRY.get(key)

    if not spec:
        return False

    selector = objective["target"]["selector"]
    filters = objective["target"]["filter"]

    # selector allowed?
    if selector not in spec.allowed_selectors:
        return False

    # required filters present?
    for field in spec.required_filter_fields[selector]:
        if field not in filters or not filters[field]:
            return False

    # operation valid?
    op = objective["operation"]
    if op["type"] != spec.operation_type:
        return False
    if op["value"] not in spec.allowed_operation_values:
        return False

    return True



def parse_atlas_output(text: str) -> dict | None:
    """
    Parse ATLAS LLM output.

    Returns:
    - objective dict (valid)
    - None if ATLAS could not form an objective
    """

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"ATLAS output must be valid JSON.\n{text}"
        ) from e

    if data is None:
        return None

    if not isinstance(data, dict):
        raise ValueError(
            f"ATLAS output must be a JSON object, got {type(data)}"
        )

    missing = REQUIRED_KEYS - data.keys()
    if missing:
        raise ValueError(
            f"ATLAS output missing required keys {missing}:\n{text}"
        )

    _validate_objective(data)

    return data
