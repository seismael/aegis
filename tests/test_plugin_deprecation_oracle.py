import os

import pytest

from aegis.core.container.app import Container
from aegis.domain.policy.models import EnforcementMode, Rule, Severity


class TestDeprecationOraclePlugin:
    """Integration test for the DeprecationOraclePlugin."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Setup a temporary workspace with the plugin."""
        plugins_dir = tmp_path / ".aegis" / "plugins"
        plugins_dir.mkdir(parents=True)

        plugin_src = os.path.join(
            os.getcwd(), ".aegis", "plugins", "deprecation_oracle.py"
        )
        with open(plugin_src, encoding="utf-8") as f:
            plugin_content = f.read()
        (plugins_dir / "deprecation_oracle.py").write_text(
            plugin_content, encoding="utf-8"
        )

        # File using deprecated pattern
        (tmp_path / "legacy_caller.py").write_text(
            "import requests\n\ndef fetch():\n    return requests.get('...')",
            encoding="utf-8",
        )

        return tmp_path

    def test_plugin_detects_deprecated_pattern(self, workspace):
        container = Container(workspace_root=str(workspace))

        rule = Rule(
            id="deprecate-requests",
            description="Moving to httpx",
            severity=Severity.MEDIUM,
            mode=EnforcementMode.BLOCK,
            metadata={
                "plugin": "deprecation-oracle",
                "deprecated_patterns": ["import requests", "requests\\.get"],
                "migration_path": "Use 'httpx.get' instead.",
            },
        )

        violations = container.evaluation_service.evaluate_workspace(
            str(workspace), [rule]
        )

        # Assertions
        assert len(violations) == 2
        assert any("import requests" in v.description for v in violations)
        assert any("httpx.get" in v.description for v in violations)
        assert "legacy_caller.py" in violations[0].file
