from typing import Dict, Any

class SendDraftTool:
    name = "send_draft"
    description = "Send an existing Gmail draft by draft ID."

    args_schema = {
        "id": {
            "type": "string",
            "required": True,
            "description": "Gmail draft ID",
        }
    }

    def __init__(self, service):
        self.service = service

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        draft_id = args["id"]

        result = (
            self.service.users()
            .drafts()
            .send(userId="me", body={"id": draft_id})
            .execute()
        )

        return result
