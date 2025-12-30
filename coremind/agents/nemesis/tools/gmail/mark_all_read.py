# coremind/agents/nemesis/tools/gmail/mark_all_read.py

from typing import Dict, Any
from coremind.agents.nemesis.tools.registry import TOOL_REGISTRY


class MarkAllReadTool:
    name = "mark_all_read"
    capabilities = {
        "domain": "email",
        "intent": "update_read_state",
        "target_selector": "all",
        "operation": {
            "type": "read_state",
            "value": "read",
        },
    }
    description = "Mark all unread LinkedIn mails as read."
    args_schema = {
        "limit": {
            "type": "integer",
            "description": "Maximum number of unread emails to mark as read",
            "required": False,
        }
    }

    def __init__(self, service):
        self.service = service

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        limit = int(args["limit"]) if "limit" in args else 10


        # --------------------------------------------------
        # Fetch unread message IDs
        # --------------------------------------------------
        response = (
            self.service.users()
            .messages()
            .list(
                userId="me",
                labelIds=["UNREAD"],
                maxResults=limit,
            )
            .execute()
        )

        messages = response.get("messages", [])
        message_ids = [m["id"] for m in messages if "id" in m]

        if not message_ids:
            return {
                "status": "noop",
                "marked_count": 0,
            }

        # --------------------------------------------------
        # Batch modify → remove UNREAD label
        # --------------------------------------------------
        self.service.users().messages().batchModify(
            userId="me",
            body={
                "ids": message_ids,
                "removeLabelIds": ["UNREAD"],
            },
        ).execute()

        return {
            "status": "marked",
            "marked_count": len(message_ids),
        }
