# coremind/agents/nemesis/tools/gmail/get_email_content.py

import base64
from typing import Dict, Any
from datetime import datetime, timezone

from tzlocal import get_localzone

from coremind.agents.nemesis.tools.registry import TOOL_REGISTRY


class GetEmailContentTool:
    name = "get_email_content"
    description = "Fetch full content for a Gmail message."
    args_schema = {
        "id": {
            "type": "string",
            "description": "The Gmail message ID",
            "required": True,
        }
    }

    def __init__(self, service):
        self.service = service

    # --------------------------------------------------
    # Gmail payload normalization
    # --------------------------------------------------

    def _normalize_gmail_date(self, message: Dict[str, Any]) -> Dict[str, str]:
        """
        Normalize Gmail internalDate into UTC + local system timezone.

        internalDate is the ONLY authoritative timestamp.
        """
        internal_ms = int(message["internalDate"])

        utc_dt = datetime.fromtimestamp(
            internal_ms / 1000,
            tz=timezone.utc,
        )

        local_tz = get_localzone()
        local_dt = utc_dt.astimezone(local_tz)

        return {
            "utc_datetime": utc_dt.isoformat(),
            "local_datetime": local_dt.isoformat(),
            "local_date": local_dt.strftime("%Y-%m-%d"),   # canonical (IRIS)
            "local_day_label": local_dt.strftime("%b %d"), # e.g. "Nov 05"
            "timezone": str(local_tz),
        }

    def _extract_email(self, message: Dict[str, Any]) -> Dict[str, Any]:
        headers = {
            h["name"].lower(): h["value"]
            for h in message.get("payload", {}).get("headers", [])
        }

        def extract_body(payload: Dict[str, Any]) -> str:
            body = payload.get("body", {})
            data = body.get("data")

            if data:
                try:
                    return base64.urlsafe_b64decode(data).decode(
                        "utf-8", errors="ignore"
                    )
                except Exception:
                    return ""

            for part in payload.get("parts", []):
                text = extract_body(part)
                if text:
                    return text

            return ""

        body_text = extract_body(message.get("payload", {}))

        # 🔒 Canonical date normalization (single source of truth)
        date_info = self._normalize_gmail_date(message)

        return {
            # 🔒 identity
            "id": message.get("id"),

            # 🔒 preview-compatible fields
            "from_": headers.get("from", ""),
            "subject": headers.get("subject", ""),
            "snippet": message.get("snippet", ""),

            # 🔒 bounded full content
            "body": (body_text or "")[:4000],

            # 🔒 canonical date block
            "date": date_info,
        }

    # --------------------------------------------------
    # Tool entry point
    # --------------------------------------------------

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        message_id = args.get("id")
        if not message_id:
            raise ValueError("Missing required argument: id")

        raw_message = (
            self.service.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="full",
            )
            .execute()
        )

        return self._extract_email(raw_message)


 
