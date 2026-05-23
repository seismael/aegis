import pytest

from aegis.domain.evaluation.plugins.interfaces import CustomAnalyzerInterface
from aegis.domain.evaluation.plugins.registry import PluginRegistry
from aegis.domain.evaluation.ports import RuleAnalyzerInterface
from aegis.domain.policy.models import Rule


class TestPluginRegistry:
    """Test suite for the PluginRegistry."""

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

    def test_custom_analyzer_interface_not_instantiable(self):
        """CustomAnalyzerInterface is an ABC and cannot be instantiated directly."""
        with pytest.raises(TypeError):
            CustomAnalyzerInterface()  # type: ignore[abstract]

    def test_loads_custom_analyzer_interface_plugin(self, tmp_path):
        """Registry loads plugins using CustomAnalyzerInterface."""
        plugin_dir = tmp_path / ".aegis" / "plugins"
        plugin_dir.mkdir(parents=True)

        plugin_code = """
from aegis.domain.evaluation.plugins.interfaces import CustomAnalyzerInterface
from aegis.domain.policy.models import Rule
from aegis.domain.evaluation.ports import ArchitecturalViolation

class MyAnalyzer(CustomAnalyzerInterface):
    def analyze_file(self, file_path, content, rules):
        return [
            ArchitecturalViolation(
                file=file_path, line=1, rule_id="custom", description="plugin check"
            )
        ]

def register_analyzers():
    return [MyAnalyzer()]
"""
        (plugin_dir / "custom_plugin.py").write_text(plugin_code, encoding="utf-8")

        registry = PluginRegistry(str(tmp_path))
        registry.load_plugins()

        assert len(registry.custom_analyzers) == 1
        assert isinstance(registry.custom_analyzers[0], CustomAnalyzerInterface)
        analyzer = registry.custom_analyzers[0]
        result = analyzer.analyze_file("test.py", "x = 1", [])
        assert len(result) == 1
        assert result[0].rule_id == "custom"

    def test_collects_mcp_tools_from_analyzer_instance(self, tmp_path):
        """Registry collects mcp_tools from CustomAnalyzerInterface instances."""
        plugin_dir = tmp_path / ".aegis" / "plugins"
        plugin_dir.mkdir(parents=True)

        plugin_code = """
from aegis.domain.evaluation.plugins.interfaces import CustomAnalyzerInterface
from aegis.domain.policy.models import Rule

class TooledAnalyzer(CustomAnalyzerInterface):
    def analyze_file(self, file_path, content, rules):
        return []

    @property
    def mcp_tools(self):
        def my_tool():
            \"\"\"A custom tool.\"\"\"
            return "ok"
        return [my_tool]

def register_analyzers():
    return [TooledAnalyzer()]
"""
        (plugin_dir / "tooled_plugin.py").write_text(plugin_code, encoding="utf-8")

        registry = PluginRegistry(str(tmp_path))
        registry.load_plugins()

        assert len(registry.custom_mcp_tools) == 1
        assert registry.custom_mcp_tools[0]() == "ok"

    def test_collects_module_level_mcp_tools(self, tmp_path):
        """Registry collects MCP tools from module-level register_mcp_tools()."""
        plugin_dir = tmp_path / ".aegis" / "plugins"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "mod_tools.py").write_text(
            """
def register_mcp_tools():
    def tool_a():
        \"\"\"Tool A.\"\"\"
        return "a"
    return [tool_a]
""",
            encoding="utf-8",
        )

        registry = PluginRegistry(str(tmp_path))
        registry.load_plugins()

        assert len(registry.custom_mcp_tools) == 1
        assert registry.custom_mcp_tools[0]() == "a"

    def test_broken_plugin_does_not_prevent_others(self, tmp_path):
        """One broken plugin doesn't prevent valid ones from loading."""
        plugin_dir = tmp_path / ".aegis" / "plugins"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "broken.py").write_text(
            "this is not valid python {{{", encoding="utf-8"
        )

        (plugin_dir / "working.py").write_text(
            """
from aegis.domain.evaluation.plugins.interfaces import CustomAnalyzerInterface
from aegis.domain.policy.models import Rule

class Good(CustomAnalyzerInterface):
    def analyze_file(self, file_path, content, rules):
        return []

def register_analyzers():
    return [Good()]
""",
            encoding="utf-8",
        )

        registry = PluginRegistry(str(tmp_path))
        registry.load_plugins()

        assert len(registry.custom_analyzers) == 1
        assert len(registry.loaded_plugins) == 1
        assert registry.loaded_plugins[0] == "working"

    def test_non_list_register_analyzers_ignored(self, tmp_path):
        """register_analyzers returning non-list is ignored."""
        plugin_dir = tmp_path / ".aegis" / "plugins"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "bad_return.py").write_text(
            """
def register_analyzers():
    return "not a list"
""",
            encoding="utf-8",
        )

        registry = PluginRegistry(str(tmp_path))
        registry.load_plugins()
        assert registry.custom_analyzers == []
        assert "bad_return" in registry.loaded_plugins

    def test_end_to_end_analysis(self, tmp_path):
        """CustomAnalyzerInterface subclass works end-to-end via the registry."""
        plugin_dir = tmp_path / ".aegis" / "plugins"
        plugin_dir.mkdir(parents=True)

        (plugin_dir / "e2e.py").write_text(
            """
from aegis.domain.evaluation.plugins.interfaces import CustomAnalyzerInterface
from aegis.domain.policy.models import Rule
from aegis.domain.evaluation.ports import ArchitecturalViolation

class E2EAnalyzer(CustomAnalyzerInterface):
    def analyze_file(self, file_path, content, rules):
        violations = []
        for rule in rules:
            if "bad" in content:
                violations.append(
                    ArchitecturalViolation(
                        file=file_path, line=1, rule_id=rule.id,
                        description="found bad pattern"
                    )
                )
        return violations

def register_analyzers():
    return [E2EAnalyzer()]
""",
            encoding="utf-8",
        )

        registry = PluginRegistry(str(tmp_path))
        registry.load_plugins()

        assert len(registry.custom_analyzers) == 1
        analyzer = registry.custom_analyzers[0]
        rules = [Rule(id="no-bad", description="No bad patterns")]
        result = analyzer.analyze_file("test.py", "something bad here", rules)
        assert len(result) == 1
        assert result[0].rule_id == "no-bad"
        assert "bad pattern" in result[0].description

        clean_result = analyzer.analyze_file("test.py", "good code", rules)
        assert clean_result == []

    def test_loaded_plugins_tracked(self, tmp_path):
        """Registry tracks loaded plugin names."""
        plugin_dir = tmp_path / ".aegis" / "plugins"
        plugin_dir.mkdir(parents=True)

        for name in ["alpha", "beta"]:
            (plugin_dir / f"{name}.py").write_text(
                f"""
from aegis.domain.evaluation.plugins.interfaces import CustomAnalyzerInterface
from aegis.domain.policy.models import Rule

class {name.capitalize()}Analyzer(CustomAnalyzerInterface):
    def analyze_file(self, file_path, content, rules):
        return []

def register_analyzers():
    return [{name.capitalize()}Analyzer()]
""",
                encoding="utf-8",
            )

        registry = PluginRegistry(str(tmp_path))
        registry.load_plugins()
        assert set(registry.loaded_plugins) == {"alpha", "beta"}
