# coremind/agents/nemesis/tools/gmail/get_email_content.py

import base64
import re
from typing import Dict, Any, List
from datetime import datetime, timezone

from tzlocal import get_localzone
from coremind.integrations.gmail.client import get_gmail_service
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

        def _clean_html(html: str) -> str:
            # 1. Remove style and script tags content
            html = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
            
            # 2. Replace common block tags with newlines for better readable structure
            html = re.sub(r'<(br|p|div|tr|h[1-6])[^>]*>', '\n', html, flags=re.IGNORECASE)
            
            # 3. Remove all remaining tags
            html = re.sub(r'<[^>]+>', ' ', html)
            
            # 4. Normalize whitespace but keep some newlines
            html = re.sub(r'[ \t]+', ' ', html) # squash spaces/tabs
            html = re.sub(r'\n\s*\n+', '\n\n', html) # normalize multiple newlines
            return html.strip()

        def extract_all_parts(payload: Dict[str, Any]) -> Dict[str, str]:
            parts = {}
            mime_type = payload.get("mimeType", "").lower()
            body = payload.get("body", {})
            data = body.get("data")

            if data:
                try:
                    text = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    parts[mime_type] = text
                except Exception:
                    pass

            for part in payload.get("parts", []):
                parts.update(extract_all_parts(part))

            return parts

        all_parts = extract_all_parts(message.get("payload", {}))
        
        # 🔒 Prefer plain text, fallback to cleaned HTML
        plain_text = all_parts.get("text/plain")
        if plain_text:
             body_text = plain_text
        else:
            html_content = all_parts.get("text/html")
            if html_content:
                body_text = _clean_html(html_content)
            else:
                body_text = ""

        # 🔒 Canonical date normalization (single source of truth)
        date_info = self._normalize_gmail_date(message)

        return {
            # 🔒 identity
            "id": message.get("id"),
            "subject": headers.get("subject", "(no subject)"),
            "from": headers.get("from", ""),
            "date": date_info,
            # 🔒 content (cleaned & safely truncated)
            "body": (body_text or "")[:10000],
            "raw_data": {
                "id": message.get("id"),
                "body": (body_text or "")[:10000],
            },
        }

    # --------------------------------------------------
    # Tool entry point
    # --------------------------------------------------

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:

        
        self.service = get_gmail_service('user_id')
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


 
