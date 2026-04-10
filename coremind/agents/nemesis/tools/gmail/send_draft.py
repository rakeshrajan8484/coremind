from typing import Dict, Any, Optional
from coremind.integrations.gmail.client import get_gmail_service

class SendDraftTool:
    name = "send_draft"
    description = (
        "Send an existing Gmail draft. "
        "If draft ID is not provided, sends the latest draft."
    )

    args_schema = {
        "id": {
            "type": "string",
            "required": False,
            "description": "Gmail draft ID (optional). If omitted, latest draft is used.",
        }
    }

    

    def _get_latest_draft_id(self) -> str:
        """
        Retrieve all drafts and return the draft ID
        with the most recent internalDate.
        """
        drafts_response = (
            self.service.users()
            .drafts()
            .list(userId="me")
            .execute()
        )

        drafts = drafts_response.get("drafts", [])
        if not drafts:
            raise RuntimeError("No drafts found in Gmail.")

        latest_draft_id: Optional[str] = None
        latest_ts: int = -1

        for d in drafts:
            draft = (
                self.service.users()
                .drafts()
                .get(userId="me", id=d["id"])
                .execute()
            )

            msg = draft.get("message", {})
            ts = int(msg.get("internalDate", 0))

            if ts > latest_ts:
                latest_ts = ts
                latest_draft_id = d["id"]

        if not latest_draft_id:
            raise RuntimeError("Unable to determine latest draft.")

        return latest_draft_id

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:

        
        self.service = get_gmail_service('user_id')
        draft_id = args.get("id")

        if not draft_id:
            draft_id = self._get_latest_draft_id()

        result = (
            self.service.users()
            .drafts()
            .send(userId="me", body={"id": draft_id})
            .execute()
        )

        return {
            "status": "sent",
            "draft_id": draft_id,
            "message_id": result.get("id"),
        }
