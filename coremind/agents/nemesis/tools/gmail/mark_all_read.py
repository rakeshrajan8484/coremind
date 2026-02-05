# coremind/agents/nemesis/tools/gmail/mark_all_read.py

from typing import Dict, Any
from coremind.agents.nemesis.tools.registry import TOOL_REGISTRY
from coremind.logging import get_logger

log = get_logger("NEMESIS.TOOL.MARK_ALL_READ")


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
    # Support explicit ids or sender-based selection
    args_schema.update({
        "ids": {
            "type": "array",
            "description": "List of message IDs to mark as read",
            "required": False,
        },
        "sender": {
            "type": "string",
            "description": "Sender address or label to filter messages",
            "required": False,
        },
    })

    def __init__(self, service):
        self.service = service

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        # Support marking by explicit ids, by sender, or by listing recent unread.
        if "ids" in args:
            message_ids = list(args["ids"]) or []
        else:
            limit = int(args["limit"]) if "limit" in args else 10
            # If a sender is provided, use Gmail search query to fetch matching messages.
            if "sender" in args and args["sender"]:
                q = f"from:{args['sender']}"
                response = (
                    self.service.users()
                    .messages()
                    .list(
                        userId="me",
                        q=q,
                        labelIds=["UNREAD"],
                        maxResults=limit,
                    )
                    .execute()
                )
            else:
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

        # Batch modify → remove UNREAD label for provided ids
        log.info("MarkAllRead: marking %d messages as read", len(message_ids))
        log.debug("MarkAllRead: ids=%s", message_ids[:20])

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
