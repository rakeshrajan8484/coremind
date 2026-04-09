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
 
tool = CheckUnreadTool()
TOOL_REGISTRY.register(tool, tool.run)

tool = GetEmailContentTool()
TOOL_REGISTRY.register(tool, tool.run)

tool = DeleteEmailTool()
TOOL_REGISTRY.register(tool, tool.run)

tool = MarkEmailTool()
TOOL_REGISTRY.register(tool, tool.run)

tool = MarkAllReadTool()
TOOL_REGISTRY.register(tool, tool.run)

tool = ListRecentEmailsTool()
TOOL_REGISTRY.register(tool, tool.run)

tool = ComposeEmailTool()
TOOL_REGISTRY.register(tool, tool.run)

tool = SendDraftTool()
TOOL_REGISTRY.register(tool, tool.run)

tool = DeleteEmailsBulkTool()
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