# coremind/agents/nemesis/tools/registry.py

from typing import Dict, Any, Iterable, List


class ToolRegistry:
    """
    Canonical, immutable-by-contract tool registry.

    Responsibilities:
    - Register tools
    - Describe tools accurately for LLMs
    - Enforce tool argument schemas at runtime
    """

    def __init__(self):
        self._tools: Dict[str, Any] = {}
        self._locked: bool = False

    # --------------------------------------------------
    # Registration
    # --------------------------------------------------

    def register(self, tool) -> None:
        if self._locked:
            raise RuntimeError("ToolRegistry is locked; registration forbidden")

        name = getattr(tool, "name", None)
        if not isinstance(name, str) or not name:
            raise ValueError("Tool must define a non-empty 'name' attribute")

        if name in self._tools:
            raise ValueError(f"Tool already registered: {name}")

        for attr in ("description", "args_schema", "run"):
            if not hasattr(tool, attr):
                raise ValueError(
                    f"Tool '{name}' missing required attribute: {attr}"
                )

        if not isinstance(tool.args_schema, dict):
            raise ValueError(
                f"Tool '{name}' args_schema must be a dict"
            )

        self._tools[name] = tool

    def lock(self) -> None:
        self._locked = True

    # --------------------------------------------------
    # Access
    # --------------------------------------------------

    def get(self, name: str):
        if name not in self._tools:
            raise KeyError(f"Tool not found: {name}")
        return self._tools[name]

    def list(self) -> Iterable[str]:
        return tuple(sorted(self._tools.keys()))

    # --------------------------------------------------
    # 🔒 Schema enforcement (NEW)
    # --------------------------------------------------

    def validate_args(self, tool_name: str, args: Dict[str, Any]) -> None:
        """
        Enforce tool argument schema strictly.

        Raises ValueError on any contract violation.
        """
        tool = self.get(tool_name)
        schema = tool.args_schema

        # Required args
        for arg, spec in schema.items():
            if spec.get("required") and arg not in args:
                raise ValueError(
                    f"Tool '{tool_name}' missing required arg: '{arg}'"
                )

        # No extra args
        for arg in args:
            if arg not in schema:
                raise ValueError(
                    f"Tool '{tool_name}' received unknown arg: '{arg}'"
                )

    # --------------------------------------------------
    # LLM-facing description (STRICT)
    # --------------------------------------------------

    def describe(self) -> List[Dict[str, Any]]:
        """
        Machine-readable tool specs.

        This is the ONLY contract the LLM sees.
        """
        specs = []

        for name, tool in sorted(self._tools.items()):
            args = {}

            for arg, spec in tool.args_schema.items():
                args[arg] = {
                    "type": spec.get("type", "string"),
                    "required": bool(spec.get("required", False)),
                    "description": spec.get("description", ""),
                }

            specs.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "args": args,
                }
            )

        return specs

    # --------------------------------------------------
    # Introspection
    # --------------------------------------------------

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        return (
            f"<ToolRegistry tools={list(self.list())} "
            f"locked={self._locked}>"
        )


TOOL_REGISTRY = ToolRegistry()
