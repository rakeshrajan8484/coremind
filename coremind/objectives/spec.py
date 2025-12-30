from dataclasses import dataclass
from typing import Dict, List, Literal

Selector = Literal["all", "single", "subset"]


@dataclass(frozen=True)
class ObjectiveSpec:
    domain: str
    intent: str
    description: str

    allowed_selectors: List[Selector]
    required_filter_fields: Dict[Selector, List[str]]

    operation_type: str
    allowed_operation_values: List[str]

    requires_concrete_identity: bool
