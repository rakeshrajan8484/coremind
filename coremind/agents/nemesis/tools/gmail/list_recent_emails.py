# coremind/agents/nemesis/tools/gmail/list_recent.py

from typing import Dict, Any, List
from datetime import datetime, timezone
from coremind.agents.nemesis.tools.registry import TOOL_REGISTRY

class ListRecentEmailsTool:
    """
    Fetch the most recent email previews regardless of read/unread status.

    This tool is meant ONLY for DISCOVERY:
    - summarization
    - semantic reference resolution
    - historical lookups

    It MUST NOT be used for state-changing operations directly.
    """

    name = "list_recent_emails"
    description = "Fetch recent email previews irrespective of read/unread status."
    args_schema = {
        "limit": {
            "type": "integer",
            "description": "Maximum number of recent emails to fetch",
            "required": False,
        }
    }

    def __init__(self, service):
        self.service = service

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
        """
        args is expected to contain:
        - limit (optional)
        - target.filter (optional, enforced locally)
        """
        limit = int(args.get("limit", 10))

        target = args.get("target", {})
        filters = target.get("filter", {})

        response = (
            self.service.users()
            .messages()
            .list(
                userId="me",
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
                continue

            date_info = self._normalize_gmail_date(internal_date)

            email = {
                "id": msg_id,
                "label": subject,
                "from": sender,
                "date": date_info,
                "source": "email",
            }

            # --------------------------------------------------
            # 🔒 APPLY DISCOVERY FILTERS (CRITICAL)
            # --------------------------------------------------

            sender_filter = filters.get("sender")
            if sender_filter:
                if sender_filter.lower() not in sender.lower():
                    continue

            brand_filter = filters.get("brand")
            if brand_filter:
                if brand_filter.lower() not in sender.lower():
                    continue

            date_filter = filters.get("date")
            if date_filter:
                # expects "Dec 23"
                if date_filter != date_info.get("local_day_label"):
                    continue

            keywords = filters.get("keywords")
            if keywords:
                haystack = f"{subject} {sender}".lower()
                if not all(k.lower() in haystack for k in keywords):
                    continue

            emails.append(email)

        return emails
