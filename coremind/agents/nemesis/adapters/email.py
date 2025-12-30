# coremind/agents/nemesis/adapters/email.py

from typing import Dict
from .types import Candidate

def email_to_candidate(email: dict) -> dict:
    return {
        "id": email.get("id"),
        "label": email.get("label", "(no subject)"),
        "from": email.get("from", ""),
        "date": email.get("date", ""),
        "source": "email"
    }


