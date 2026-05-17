from aegis.core.plugins.registry import PluginRegistry
from aegis.domain.evaluation.ports import RuleAnalyzerInterface


class TestPluginRegistry:
    """
    Test suite for the PluginRegistry.
    """

    def test_no_plugin_dir_does_not_crash(self, tmp_path):
        registry = PluginRegistry(str(tmp_path))
        registry.load_plugins()  # Should not raise
        assert registry.custom_analyzers == []
        assert registry.custom_mcp_tools == []

    def test_empty_plugin_dir_does_not_crash(self, tmp_path):
        plugin_dir = tmp_path / ".aegis" / "plugins"
        plugin_dir.mkdir(parents=True)

        registry = PluginRegistry(str(tmp_path))
        registry.load_plugins()
        assert registry.custom_analyzers == []
        assert registry.custom_mcp_tools == []

    def test_skips_non_py_files(self, tmp_path):
        plugin_dir = tmp_path / ".aegis" / "plugins"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "readme.txt").write_text("not a plugin", encoding="utf-8")
        (plugin_dir / "__init__.py").write_text("", encoding="utf-8")

        registry = PluginRegistry(str(tmp_path))
        registry.load_plugins()
        assert registry.custom_analyzers == []
        assert registry.custom_mcp_tools == []

    def test_loads_valid_plugin_with_analyzers(self, tmp_path):
        plugin_dir = tmp_path / ".aegis" / "plugins"
        plugin_dir.mkdir(parents=True)

        plugin_code = """
from aegis.domain.evaluation.ports import RuleAnalyzerInterface

class CustomAnalyzer(RuleAnalyzerInterface):
    def analyze_file(self, file_path, content, rules):
        return []

def register_analyzers():
    return [CustomAnalyzer()]

def register_mcp_tools():
    return []
"""
        (plugin_dir / "my_plugin.py").write_text(plugin_code, encoding="utf-8")

        registry = PluginRegistry(str(tmp_path))
        registry.load_plugins()

        assert len(registry.custom_analyzers) == 1
        assert isinstance(registry.custom_analyzers[0], RuleAnalyzerInterface)

    def test_loads_plugin_with_tools(self, tmp_path):
        plugin_dir = tmp_path / ".aegis" / "plugins"
        plugin_dir.mkdir(parents=True)

        plugin_code = """
def my_custom_tool(param: str) -> str:
    return f"Processed {param}"

def register_analyzers():
    return []

def register_mcp_tools():
    return [my_custom_tool]
"""
        (plugin_dir / "tool_plugin.py").write_text(plugin_code, encoding="utf-8")

        registry = PluginRegistry(str(tmp_path))
        registry.load_plugins()

        assert len(registry.custom_mcp_tools) == 1
        assert registry.custom_mcp_tools[0].__name__ == "my_custom_tool"

    def test_invalid_plugin_logs_error(self, tmp_path):
        plugin_dir = tmp_path / ".aegis" / "plugins"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "broken.py").write_text(
            "this is not valid python >>> syntax error", encoding="utf-8"
        )

        registry = PluginRegistry(str(tmp_path))
        # Should log error, not crash
        registry.load_plugins()
        assert registry.custom_analyzers == []
        assert registry.custom_mcp_tools == []
