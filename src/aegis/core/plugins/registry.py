import os
import importlib.util
import structlog
from typing import Callable, List
from aegis.domain.evaluation.ports import ASTAnalyzerInterface

logger = structlog.get_logger()


class PluginRegistry:
    """
    Enterprise Extensibility Hub.
    Dynamically loads custom user-defined architectural rules and analyzers
    from the workspace's `.aegis/plugins/` directory without requiring
    modifications to the Aegis core engine.
    """

    def __init__(self, workspace_root: str):
        self.plugin_dir = os.path.join(workspace_root, ".aegis", "plugins")
        self.custom_analyzers: List[ASTAnalyzerInterface] = []
        self.custom_mcp_tools: List[Callable] = []

    def load_plugins(self):
        """Scans .aegis/plugins/ and hot-loads Python modules."""
        if not os.path.isdir(self.plugin_dir):
            logger.info("No plugin directory found", path=self.plugin_dir)
            return

        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                self._load_module(filename)

    def _load_module(self, filename: str):
        filepath = os.path.join(self.plugin_dir, filename)
        module_name = f"aegis_plugin_{filename[:-3]}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                if hasattr(module, "register_analyzers"):
                    analyzers = module.register_analyzers()
                    self.custom_analyzers.extend(analyzers)
                    logger.info(
                        "Registered custom analyzers",
                        plugin=filename,
                        count=len(analyzers),
                    )

                if hasattr(module, "register_mcp_tools"):
                    tools = module.register_mcp_tools()
                    self.custom_mcp_tools.extend(tools)
                    logger.info(
                        "Registered custom MCP tools",
                        plugin=filename,
                        count=len(tools),
                    )

                logger.info("Aegis Plugin loaded successfully", plugin=filename)
        except Exception as e:
            logger.error(
                "Failed to load Aegis plugin",
                plugin=filename,
                error=str(e),
            )
