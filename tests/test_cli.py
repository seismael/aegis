import json
import os
from unittest.mock import MagicMock

from typer.testing import CliRunner

from aegis.cli.main import AegisCLI
from aegis.core.models.governance import EnforcementMode, Rule, Severity
from aegis.domain.evaluation.ports import ArchitecturalViolation

runner = CliRunner()


class TestAegisCLI:
    """Test suite for the AegisCLI — user-facing commands."""

    def _mock_container(self):
        c = MagicMock()
        c.workspace_root = "/fake/project"
        c.policy_parser.parse_rules.return_value = []
        c.evaluation_service.evaluate_workspace.return_value = []
        c.evaluation_service.evaluate_changes.return_value = []
        c.baseline_manager.load_baseline_raw.return_value = []
        c.baseline_manager.is_exempt.return_value = False
        c.loaded_plugins = []
        return c

    def _cli(self, container=None):
        return AegisCLI(container=container or self._mock_container())

    def test_status_json_empty(self):
        """status --json returns valid JSON with no rules."""
        cli = self._cli()
        result = runner.invoke(cli.app, ["status", "--json"])
        assert result.exit_code == 0

    def test_status_with_baseline(self):
        """status does not crash when baseline has entries (regression: dict vs attrs)."""
        container = self._mock_container()
        container.baseline_manager.load_baseline_raw.return_value = [
            {"file": "src/main.py", "line": 10, "rule_id": "r1"}
        ]
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["status", "--json"])
        assert result.exit_code == 0

    def test_check_no_rules_file(self, tmp_path):
        """check exits 1 when rules.yaml missing."""
        container = self._mock_container()
        container.workspace_root = str(tmp_path)
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["check"])
        assert result.exit_code == 1
        assert "rules.yaml not found" in result.stdout

    def test_check_compliant(self, tmp_path):
        """check prints compliant when no violations."""
        container = self._mock_container()
        rules_dir = os.path.join(str(tmp_path), ".aegis")
        os.makedirs(rules_dir, exist_ok=True)
        rules_file = os.path.join(rules_dir, "rules.yaml")
        with open(rules_file, "w", encoding="utf-8") as f:
            f.write("rules: []")
        container.workspace_root = str(tmp_path)
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["check"])
        assert result.exit_code == 0
        assert "Architecture compliant" in result.stdout

    def test_check_blocking_violation_exits_1(self, tmp_path):
        """check exits 1 when blocking violations found."""
        container = self._mock_container()
        rules_dir = os.path.join(str(tmp_path), ".aegis")
        os.makedirs(rules_dir, exist_ok=True)
        rules_file = os.path.join(rules_dir, "rules.yaml")
        with open(rules_file, "w", encoding="utf-8") as f:
            f.write("rules: [{\"id\": \"r1\", \"description\": \"test\", \"severity\": \"HIGH\", \"mode\": \"block\"}]")
        container.workspace_root = str(tmp_path)
        container.policy_parser.parse_rules.return_value = [
            Rule(id="r1", description="test", severity=Severity.HIGH, mode=EnforcementMode.BLOCK)
        ]
        container.evaluation_service.evaluate_workspace.return_value = [
            ArchitecturalViolation(file="src/main.py", line=1, rule_id="r1", description="test")
        ]
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["check"])
        assert result.exit_code == 1
        assert "Blocked" in result.stdout

    def test_check_unknown_rule_violation_no_crash(self, tmp_path):
        """check handles violation with unknown rule_id without AttributeError."""
        container = self._mock_container()
        rules_dir = os.path.join(str(tmp_path), ".aegis")
        os.makedirs(rules_dir, exist_ok=True)
        rules_file = os.path.join(rules_dir, "rules.yaml")
        with open(rules_file, "w", encoding="utf-8") as f:
            f.write("rules: []")
        container.workspace_root = str(tmp_path)
        container.policy_parser.parse_rules.return_value = []
        container.evaluation_service.evaluate_workspace.return_value = [
            ArchitecturalViolation(file="src/main.py", line=1, rule_id="nonexistent", description="test")
        ]
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["check"])
        assert result.exit_code == 0
