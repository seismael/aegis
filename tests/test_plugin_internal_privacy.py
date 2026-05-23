import os

import pytest

from aegis.domain.policy.models import EnforcementMode, Rule, Severity


class TestInternalPrivacyPlugin:
    """Integration test for the InternalPrivacyPlugin."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Setup a temporary workspace with the plugin and a privacy boundary."""
        plugins_dir = tmp_path / ".aegis" / "plugins"
        plugins_dir.mkdir(parents=True)

        plugin_src = os.path.join(
            os.getcwd(), ".aegis", "plugins", "internal_privacy.py"
        )
        with open(plugin_src, encoding="utf-8") as f:
            plugin_content = f.read()
        (plugins_dir / "internal_privacy.py").write_text(
            plugin_content, encoding="utf-8"
        )

        # Private module
        core_dir = tmp_path / "src" / "myapp" / "core"
        core_dir.mkdir(parents=True)
        (core_dir / "secret_logic.py").write_text(
            "class Secret: pass", encoding="utf-8"
        )

        # Authorized consumer
        (core_dir / "container.py").write_text(
            "from myapp.core import secret_logic", encoding="utf-8"
        )

        # Unauthorized consumer
        api_dir = tmp_path / "src" / "myapp" / "api"
        api_dir.mkdir(parents=True)
        (api_dir / "public_endpoint.py").write_text(
            "from myapp.core import secret_logic", encoding="utf-8"
        )

        return tmp_path

    def test_plugin_detects_unauthorized_access(self, workspace):
        container = Container(workspace_root=str(workspace))

        rule = Rule(
            id="privacy-test",
            description="Test internal privacy",
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
            metadata={
                "plugin": "internal-privacy",
                "private_module": "secret_logic",
                "authorized_consumers": ["core\\.container"],
            },
        )

        violations = container.evaluation_service.evaluate_workspace(
            str(workspace), [rule]
        )

        # Assertions
        assert len(violations) == 1
        assert "public_endpoint.py" in violations[0].file
        assert "Internal Privacy Violation" in violations[0].description

        # Verify authorized consumer is NOT flagged
        assert not any("container.py" in v.file for v in violations)
