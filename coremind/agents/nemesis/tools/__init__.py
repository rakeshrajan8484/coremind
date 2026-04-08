from coremind.integrations.gmail.client import get_gmail_service
from coremind.agents.nemesis.tools.gmail.list_recent_emails import ListRecentEmailsTool
from coremind.agents.nemesis.tools.gmail.check_unread import CheckUnreadTool
from coremind.agents.nemesis.tools.gmail.get_email_content import GetEmailContentTool
from coremind.agents.nemesis.tools.gmail.delete_email import DeleteEmailTool
from coremind.agents.nemesis.tools.gmail.mark_email import MarkEmailTool
from coremind.agents.nemesis.tools.gmail.mark_all_read import MarkAllReadTool
from coremind.agents.nemesis.tools.gmail.compose_email import ComposeEmailTool
from coremind.agents.nemesis.tools.gmail.send_draft import SendDraftTool
from coremind.agents.nemesis.tools.gmail.delete_emails_bulk import DeleteEmailsBulkTool
from coremind.agents.nemesis.tools.smart_home_control import SmartHomeControlTool

import coremind.agents.nemesis.tools 
from coremind.agents.nemesis.tools.registry import TOOL_REGISTRY
 
gmail_service = get_gmail_service()

tool = CheckUnreadTool(gmail_service)
TOOL_REGISTRY.register(tool, tool.run)

tool = GetEmailContentTool(gmail_service)
TOOL_REGISTRY.register(tool, tool.run)

tool = DeleteEmailTool(gmail_service)
TOOL_REGISTRY.register(tool, tool.run)

tool = MarkEmailTool(gmail_service)
TOOL_REGISTRY.register(tool, tool.run)

tool = MarkAllReadTool(gmail_service)
TOOL_REGISTRY.register(tool, tool.run)

tool = ListRecentEmailsTool(gmail_service)
TOOL_REGISTRY.register(tool, tool.run)

tool = ComposeEmailTool(gmail_service)
TOOL_REGISTRY.register(tool, tool.run)

tool = SendDraftTool(gmail_service)
TOOL_REGISTRY.register(tool, tool.run)

tool = DeleteEmailsBulkTool(gmail_service)
TOOL_REGISTRY.register(tool, tool.run)

tool = SmartHomeControlTool()
TOOL_REGISTRY.register(tool, tool.run)
__all__ = [
    "CheckUnreadTool",
    "GetEmailContentTool",
    "DeleteEmailTool",
    "MarkEmailTool",
    "MarkAllReadTool",
    "ListRecentEmailsTool",
    "ComposeEmailTool",
    "SendDraftTool",
    "DeleteEmailsBulkTool",
]