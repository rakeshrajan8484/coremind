from coremind.agents.nemesis.tools.registry import TOOL_REGISTRY
from coremind.logging import get_logger
from coremind.integrations.gmail.client import get_gmail_service

log = get_logger("NEMESIS.TOOLS.GMAIL.DELETE")

class DeleteEmailTool:
    name = "delete_email"
    description = "Delete an email. If message ID is missing, retrieve candidates first."
    capabilities = {
        "domain": "email",
        "intent": "delete_messages",
        "target_selector": "all",
    }
    args_schema = {
        "id": {
            "type": "string",
            "description": "The Gmail message ID to delete",
            "required": True,
        }
    }

     

    def run(self, args: dict):
        self.service = get_gmail_service()
        message_id = args.get("id")
        log.error("DELETE TOOL SCOPES: %s", self.service._http.credentials.scopes)

        # -------------------------------------------------
        # 🔍 BOOTSTRAP: retrieve candidates if ID missing
        # -------------------------------------------------
        if not message_id:
            check_unread = TOOL_REGISTRY.get("check_unread")
            if not check_unread:
                raise RuntimeError("check_unread tool not registered")

            result = check_unread.run({})

            candidates = result.get("candidates", [])
            if not candidates:
                return {
                    "status": "not_found",
                    "message": "No emails found to delete",
                }

            # 🔒 Deterministic selection (latest email)
            message_id = candidates[0]["id"]

        self.service.users().messages().trash(
            userId="me",
            id=message_id,
        ).execute()

        return {
            "status": "deleted",
            "id": message_id,
        }
