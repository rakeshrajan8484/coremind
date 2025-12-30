from typing import Any, Dict, List, Optional
from pydantic import BaseModel

class PlanStep(BaseModel):
    action: str
    args: Dict[str, Any] = {}

class Plan(BaseModel):
    steps: List[PlanStep]
