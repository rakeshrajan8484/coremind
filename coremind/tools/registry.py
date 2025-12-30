from coremind.agents.nemesis.tools.registry import ToolRegistry
from coremind.agents.nemesis.tools.gmail.check_unread import CheckUnreadTool
from coremind.agents.nemesis.tools.gmail.get_email_content import GetEmailContentTool
from coremind.agents.nemesis.tools.gmail.list_recent_emails import ListRecentEmailsTool

registry = ToolRegistry()
registry.register(CheckUnreadTool, CheckUnreadTool.run)
registry.register(GetEmailContentTool, GetEmailContentTool.run)
registry.register(ListRecentEmailsTool, ListRecentEmailsTool.run)