from collections.abc import Callable

from aegis.domain.evaluation.ports import RuleAnalyzerInterface


class CustomAnalyzerInterface(RuleAnalyzerInterface):
    """
    Interface for third-party custom analyzers.
    Plugin authors subclass this and return instances from register_analyzers().

    Optionally expose MCP tools via the mcp_tools property — these are
    auto-registered with the kernel when the plugin loads.
    """

    @property
    def mcp_tools(self) -> list[Callable]:
        """Optional list of MCP tool functions for the kernel to register."""
        return []
