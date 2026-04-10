# coremind/agents/nemesis/tools/gmail/check_unread.py

from typing import Dict, Any, List
from datetime import datetime, timezone
from coremind.integrations.gmail.client import get_gmail_service

from coremind.agents.nemesis.tools.registry import TOOL_REGISTRY


class CheckUnreadTool:
    name = "check_unread"
    description = "Fetch unread email previews."
    args_schema = {
        "limit": {
            "type": "integer",
            "description": "Maximum number of unread emails to fetch",
            "required": False,
        }
    }

    

    # --------------------------------------------------
    # Date normalization (shared invariant)
    # --------------------------------------------------

    def _get_system_timezone(self):
        """
        Resolve system timezone without hardcoding.
        """
        try:
            return datetime.now().astimezone().tzinfo
        except Exception:
            return timezone.utc

    def _normalize_gmail_date(self, internal_date_ms: str) -> Dict[str, str]:
        """
        Normalize Gmail internalDate (epoch ms) into UTC + local time.
        """
        utc_dt = datetime.fromtimestamp(
            int(internal_date_ms) / 1000,
            tz=timezone.utc,
        )

        local_tz = self._get_system_timezone()
        local_dt = utc_dt.astimezone(local_tz)

        return {
            "utc_datetime": utc_dt.isoformat(),
            "local_datetime": local_dt.isoformat(),
            "local_date": local_dt.strftime("%Y-%m-%d"),   # canonical
            "local_day_label": local_dt.strftime("%b %d"), # e.g. "Nov 05"
            "timezone": str(local_tz),
        }

    # --------------------------------------------------
    # Tool entry point
    # --------------------------------------------------

    def run(self, args: Dict[str, Any]) -> List[Dict[str, Any]]:
         
        
        self.service = get_gmail_service('user_id')
        limit = int(args["limit"]) if "limit" in args else 10

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

        message_refs = response.get("messages", [])
        emails: List[Dict[str, Any]] = []

        for ref in message_refs:
            msg_id = ref.get("id")
            if not msg_id:
                continue

            msg = (
                self.service.users()
                .messages()
                .get(
                    userId="me",
                    id=msg_id,
                    format="full",
                )
                .execute()
            )

            headers = {
                h["name"].lower(): h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }

            subject = headers.get("subject", "(no subject)")
            sender = headers.get("from", "")

            internal_date = msg.get("internalDate")
            if not internal_date:
                # Gmail guarantees this, but guard anyway
                continue

            date_info = self._normalize_gmail_date(internal_date)

            emails.append(
                {
                    "id": msg_id,
                    "label": subject,
                    "from": sender,
                    "date": date_info,   # 🔒 structured, canonical
                    "source": "email",
                }
            )

        return emails


 