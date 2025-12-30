from coremind.integrations.gmail.client import get_gmail_service
from coremind.agents.nemesis.tools.gmail.list_recent_emails import ListRecentEmailsTool
from coremind.agents.nemesis.tools.gmail.check_unread import CheckUnreadTool
from coremind.agents.nemesis.tools.gmail.get_email_content import GetEmailContentTool
from coremind.agents.nemesis.tools.gmail.delete_email import DeleteEmailTool
from coremind.agents.nemesis.tools.gmail.mark_email import MarkEmailTool
from coremind.agents.nemesis.tools.gmail.mark_all_read import MarkAllReadTool

import coremind.agents.nemesis.tools 
from coremind.agents.nemesis.tools.registry import TOOL_REGISTRY
 
gmail_service = get_gmail_service()

TOOL_REGISTRY.register(CheckUnreadTool(gmail_service))
TOOL_REGISTRY.register(GetEmailContentTool(gmail_service))
TOOL_REGISTRY.register(DeleteEmailTool(gmail_service))
TOOL_REGISTRY.register(MarkEmailTool(gmail_service))
TOOL_REGISTRY.register(MarkAllReadTool(gmail_service))
TOOL_REGISTRY.register(ListRecentEmailsTool(gmail_service))
__all__ = [
    "CheckUnreadTool",
    "GetEmailContentTool",
    "DeleteEmailTool",
    "MarkEmailTool",
    "MarkAllReadTool",
    "ListRecentEmailsTool",
]