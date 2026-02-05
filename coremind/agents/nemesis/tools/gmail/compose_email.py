import base64
from email.message import EmailMessage

from coremind.agents.nemesis.tools.registry import TOOL_REGISTRY
from coremind.logging import get_logger

log = get_logger("NEMESIS.TOOLS.GMAIL.COMPOSE")


class ComposeEmailTool:
    name = "compose_message"
    description = "Compose an email draft using Gmail (does not send)"

    capabilities = {
        "domain": "email",
        "intent": "compose_message",
        "target_selector": "new",   # 🔒 CRITICAL
    }

    args_schema = {
        "to": {
            "type": "string",
            "description": "Recipient email address",
            "required": True,
        },
        "body": {
            "type": "string",
            "description": "Email body text",
            "required": True,
        },
        "subject": {
            "type": "string",
            "description": "Email subject",
            "required": False,
        },
    }

    def __init__(self, service):
        self.service = service

    def run(self, args: dict):
        to_email = args["to"]
        body = args["body"]
        subject = args.get("subject", "Mail from CoreMind")

        log.info("Composing email draft to %s", to_email)

        email = EmailMessage()
        email["To"] = to_email
        email["From"] = "me"
        email["Subject"] = subject
        email.set_content(body)

        encoded_message = base64.urlsafe_b64encode(
            email.as_bytes()
        ).decode("utf-8")

        # ---------------------------------------------
        # Create draft (NOT send)
        # ---------------------------------------------
        result = (
            self.service.users()
            .drafts()
            .create(
                userId="me",
                body={"message": {"raw": encoded_message}},
            )
            .execute()
        )

        return {
            "status": "drafted",
            "draft_id": result.get("id"),
            "to": to_email,
            "subject": subject,
        }

 
