import importlib.util
import os
from collections.abc import Callable

import structlog

from aegis.domain.evaluation.ports import RuleAnalyzerInterface

logger = structlog.get_logger()


class PluginRegistry:
    """Dynamic loader for user-defined plugins from `.aegis/plugins/`."""

    def __init__(self, workspace_root: str):
        self.plugin_dir = os.path.join(workspace_root, ".aegis", "plugins")
        self.custom_analyzers: list[RuleAnalyzerInterface] = []
        self.custom_mcp_tools: list[Callable] = []
        self._loaded: list[str] = []

    def load_plugins(self):
        """Scan .aegis/plugins/ and hot-load Python modules."""
        if not os.path.isdir(self.plugin_dir):
            logger.debug("No plugin directory found", path=self.plugin_dir)
            return

        for filename in sorted(os.listdir(self.plugin_dir)):
            if filename.endswith(".py") and not filename.startswith("__"):
                self._load_module(filename)

    @property
    def loaded_plugins(self) -> list[str]:
        """Names of successfully loaded plugin modules."""
        return list(self._loaded)

    def _load_module(self, filename: str):
        filepath = os.path.join(self.plugin_dir, filename)
        module_name = f"aegis_plugin_{filename[:-3]}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if not spec or not spec.loader:
                logger.warning("Plugin spec could not be loaded", plugin=filename)
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "register_analyzers"):
                analyzers = module.register_analyzers()
                if not isinstance(analyzers, list):
                    raise TypeError(
                        f"register_analyzers() must return a list, got {type(analyzers).__name__}"
                    )
                self.custom_analyzers.extend(analyzers)
                logger.info(
                    "Plugin registered analyzers",
                    plugin=filename,
                    count=len(analyzers),
                )

            if hasattr(module, "register_mcp_tools"):
                tools = module.register_mcp_tools()
                if not isinstance(tools, list):
                    raise TypeError(
                        f"register_mcp_tools() must return a list, got {type(tools).__name__}"
                    )
                for t in tools:
                    if not callable(t):
                        raise TypeError(
                            f"MCP tool must be callable, got {type(t).__name__}"
                        )
                self.custom_mcp_tools.extend(tools)
                logger.info(
                    "Plugin registered MCP tools",
                    plugin=filename,
                    count=len(tools),
                )

            if hasattr(module, "register_analyzers") or hasattr(
                module, "register_mcp_tools"
            ):
                self._loaded.append(filename)
                logger.info("Plugin loaded", plugin=filename)
            else:
                logger.warning(
                    "Plugin has no register_analyzers or register_mcp_tooks",
                    plugin=filename,
                )

        except Exception as e:
            logger.error(
                "Failed to load Aegis plugin",
                plugin=filename,
                error=str(e),
            )
