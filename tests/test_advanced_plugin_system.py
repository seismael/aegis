import os

import pytest


class TestAdvancedPluginArchitecture:
    """Integration test for the enhanced plugin lifecycle and capabilities."""

    @pytest.fixture
    def workspace(self, tmp_path):
        # 1. Create .aegis/plugins dir
        plugins_dir = tmp_path / ".aegis" / "plugins"
        plugins_dir.mkdir(parents=True)

        # 2. Copy the dead module detector into the temp workspace
        plugin_src = os.path.join(
            os.getcwd(), ".aegis", "plugins", "dead_module_detector.py"
        )
        with open(plugin_src, encoding="utf-8") as f:
            plugin_content = f.read()
        (plugins_dir / "dead_module_detector.py").write_text(
            plugin_content, encoding="utf-8"
        )

        # 3. Create a project structure
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "main.py").write_text(
            "import src.useful\ndef start(): pass", encoding="utf-8"
        )
        (src_dir / "useful.py").write_text("def tool(): pass", encoding="utf-8")

        # This one is dead (never imported)
        (src_dir / "ghost.py").write_text("def spooky(): pass", encoding="utf-8")

        return tmp_path

    def test_auto_rule_registration(self, workspace):
        """Verify that plugins can automatically register their own rules."""
        container = Container(workspace_root=str(workspace))
        rules = container.load_rules()

        # Should include the dead-module-detection rule from the plugin
        rule_ids = [r.id for r in rules]
        assert "dead-module-detection" in rule_ids

    def test_project_wide_analysis(self, workspace):
        """Verify that plugins can perform whole-project analysis."""
        container = Container(workspace_root=str(workspace))
        rules = container.load_rules()

        violations = container.evaluation_service.evaluate_workspace(
            str(workspace), rules
        )

        relevant = [v for v in violations if v.rule_id == "dead-module-detection"]

        # Should find 'ghost.py' but not 'useful.py' or 'main.py'
        assert len(relevant) == 1
        assert "ghost.py" in relevant[0].file
        assert "ghost" in relevant[0].description

    def test_custom_remediation_provider(self, workspace):
        """Verify that plugins can provide specialized remediation text."""
        container = Container(workspace_root=str(workspace))
        rules = container.load_rules()
        rules_map = {r.id: r for r in rules}

        violations = container.evaluation_service.evaluate_workspace(
            str(workspace), rules
        )

        relevant = [v for v in violations if v.rule_id == "dead-module-detection"]

        # Generate remediation prompt
        prompt = container.remediation_synthesizer.generate_remediation(
            relevant, rules_map
        )

        # Should use the custom remediation provided by the plugin
        assert "surface area" in prompt.handoff_prompt
        assert "Dead Module Detected" in prompt.handoff_prompt
