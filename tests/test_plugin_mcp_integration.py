class TestPluginMCPIntegration:
    """
    Suite for plugin integration verification.
    """

    def test_plugin_registry_provides_custom_tools(self, tmp_path):
        """Verify PluginRegistry correctly exposes custom MCP tools."""
        from aegis.core.plugins.registry import PluginRegistry

        # Create a test plugin
        plugin_dir = tmp_path / ".aegis" / "plugins"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "test_tool.py").write_text(
            """
def my_tool(param: str) -> str:
    return f"processed {param}"

def register_mcp_tools():
    return [my_tool]
""",
            encoding="utf-8",
        )

        registry = PluginRegistry(str(tmp_path))
        registry.load_plugins()

        assert len(registry.custom_mcp_tools) == 1
        assert registry.custom_mcp_tools[0].__name__ == "my_tool"
        # Verify the tool is callable and returns the expected result
        result = registry.custom_mcp_tools[0]("test")
        assert result == "processed test"
