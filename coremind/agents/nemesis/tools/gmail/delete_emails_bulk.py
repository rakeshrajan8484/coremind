from typing import Dict, Any, List
from coremind.agents.nemesis.tools.registry import TOOL_REGISTRY
from coremind.logging import get_logger
from coremind.integrations.gmail.client import get_gmail_service

log = get_logger("NEMESIS.TOOLS.GMAIL.DELETE_BULK")


class DeleteEmailsBulkTool:
    """
    Delete multiple emails matching a filter (sender/date/etc)
    or an explicit list of message IDs.
    """

    name = "delete_emails_bulk"
    description = "Bulk delete multiple emails by IDs or sender"
    capabilities = {
        "domain": "email",
        "intent": "delete_messages_bulk",
        "target_selector": "all",
    }

    args_schema = {
        "ids": {
            "type": "array",
            "items": {"type": "string"},
            "required": False,
        },
        "sender": {
            "type": "string",
            "required": False,
        },
    }

     

    def _search_ids(self, sender: str) -> List[str]:
        query = f"from:{sender}"
        ids: List[str] = []

        response = self.service.users().messages().list(
            userId="me",
            q=query,
            maxResults=500,
        ).execute()

        for m in response.get("messages", []):
            ids.append(m["id"])

        return ids

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        self.service = get_gmail_service()
        ids: List[str] | None = args.get("ids")
        sender: str | None = args.get("sender")

        if not ids:
            if not sender:
                raise RuntimeError(
                    "Bulk delete requires either 'ids' or 'sender'"
                )

            log.info("Resolving bulk delete IDs for sender=%s", sender)
            ids = self._search_ids(sender)

        if not ids:
            return {
                "status": "success",
                "summary": "No matching emails found",
                "artifacts": {
                    "deleted": 0,
                },
            }

        for msg_id in ids:
            self.service.users().messages().trash(
                userId="me",
                id=msg_id,
            ).execute()

        # 🔒 CRITICAL: TERMINATION SIGNAL
        return {
            "status": "success",
            "summary": f"Deleted {len(ids)} emails",
            "artifacts": {
                "deleted": len(ids),
                "ids": ids,
                "force_done": True,   # 🔑 THIS STOPS NEMESIS
            },
        }

