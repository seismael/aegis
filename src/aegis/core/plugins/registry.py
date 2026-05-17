import importlib.util
import os
import sys
from collections.abc import Callable

import structlog

from aegis.core.plugins.interfaces import CustomAnalyzerInterface
from aegis.domain.evaluation.ports import RuleAnalyzerInterface

logger = structlog.get_logger()


class PluginRegistry:
    """
    Dynamically loads custom analyzers and MCP tools from the workspace's .aegis/plugins/ directory.
    Provides Inversion of Control (IoC) for enterprise-specific governance rules.
    """

    def __init__(self, workspace_root: str):
        self.plugin_dir = os.path.join(workspace_root, ".aegis", "plugins")
        self.custom_analyzers: list[RuleAnalyzerInterface] = []
        self.custom_mcp_tools: list[Callable] = []
        self.loaded_plugins: list[str] = []

    def load_plugins(self) -> None:
        if not os.path.exists(self.plugin_dir):
            return

        # Add plugin dir to sys.path so plugins can import local helpers if needed
        if self.plugin_dir not in sys.path:
            sys.path.insert(0, self.plugin_dir)

        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                self._load_plugin_file(filename)

    def _load_plugin_file(self, filename: str) -> None:
        module_name = filename[:-3]
        file_path = os.path.join(self.plugin_dir, filename)

        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Hook 1: Custom Analyzers
            if hasattr(module, "register_analyzers"):
                analyzers = module.register_analyzers()
                if isinstance(analyzers, list):
                    self.custom_analyzers.extend(analyzers)
                    # Collect MCP tools from CustomAnalyzerInterface instances
                    for a in analyzers:
                        if isinstance(a, CustomAnalyzerInterface):
                            self.custom_mcp_tools.extend(a.mcp_tools)

            # Hook 2: Custom MCP Tools
            if hasattr(module, "register_mcp_tools"):
                tools = module.register_mcp_tools()
                if isinstance(tools, list):
                    self.custom_mcp_tools.extend(tools)

            self.loaded_plugins.append(module_name)
            logger.info("Aegis plugin loaded", plugin=module_name)

        except Exception as e:
            logger.error("Failed to load plugin", plugin=filename, error=str(e))
