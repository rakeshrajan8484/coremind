# coremind/agents/nemesis/tools/gmail/mark_email.py

from coremind.logging import get_logger
from coremind.integrations.gmail.client import get_gmail_service

log = get_logger("NEMESIS.TOOL.MARK_EMAIL")


class MarkEmailTool:
    name = "mark_email"
    description = "Mark a Gmail message as read or unread."
    args_schema = {
        "id": {
            "type": "string",
            "required": True,
            "description": "Gmail message ID",
        },
        "state": {
            "type": "string",
            "required": True,
            "description": "read or unread",
        },
    }

    

    def run(self, args: dict):
        self.service = get_gmail_service()
        msg_id = args.get("id")
        if not msg_id:
            raise ValueError("mark_email requires message id")

        state = args.get("state")

        if not msg_id:
            raise ValueError("mark_email requires message id")

        if state not in ("read", "unread"):
            raise ValueError("state must be 'read' or 'unread'")

        log.info("Marking email %s as %s", msg_id, state)

        labels_to_add = []
        labels_to_remove = []

        if state == "read":
            labels_to_remove = ["UNREAD"]
        else:
            labels_to_add = ["UNREAD"]

        # Gmail MODIFY is a mutation — operate on messages when a message id is provided
        self.service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={
                "addLabelIds": labels_to_add,
                "removeLabelIds": labels_to_remove,
            },
        ).execute()

        return {
            "status": "success",
            "id": msg_id,
            "state": state,
        }
