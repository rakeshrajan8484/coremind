# coremind/agents/nemesis/adapters/types.py

from typing import TypedDict, Optional


class Candidate(TypedDict):
    id: str
    label: str
    source: Optional[str]
