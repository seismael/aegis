import json
import os
from unittest.mock import MagicMock

from typer.testing import CliRunner

from aegis.cli.main import AegisCLI
from aegis.core.models.governance import EnforcementMode, EngineType, Rule, Severity
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
        c.remediation_synthesizer.generate_remediation.return_value = "mock prompt"
        return c

    def _cli(self, container=None):
        return AegisCLI(container=container or self._mock_container())

    def test_status_json_empty(self):
        """status --json returns valid JSON with no rules."""
        cli = self._cli()
        result = runner.invoke(cli.app, ["status", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout)
        assert "engines" in data
        assert "plugins" in data
        assert "rules" in data
        assert "active_violations" in data

    def test_status_with_baseline(self):
        """status does not crash when baseline has entries (regression: dict vs attrs)."""
        container = self._mock_container()
        container.baseline_manager.load_baseline_raw.return_value = [
            {"file": "src/main.py", "line": 10, "rule_id": "r1"}
        ]
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["status", "--json"])
        assert result.exit_code == 0

    def test_status_engine_counts(self):
        """status reflects engine distribution."""
        container = self._mock_container()
        container.policy_parser.parse_rules.return_value = [
            Rule(id="r1", description="ts", engine_type=EngineType.TREE_SITTER),
            Rule(id="r2", description="graph", engine_type=EngineType.GRAPH),
        ]
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["status", "--json"])
        data = json.loads(result.stdout)
        assert data["rules_count"] == 2
        assert data["engines"]["tree-sitter"] == 1
        assert data["engines"]["graph"] == 1

    def test_status_with_active_violations(self):
        """status reports active (non-baseline-exempt) violations."""
        container = self._mock_container()
        container.policy_parser.parse_rules.return_value = [
            Rule(id="r1", description="test")
        ]
        container.evaluation_service.evaluate_workspace.return_value = [
            ArchitecturalViolation(file="x.py", line=1, rule_id="r1", description="bad")
        ]
        container.baseline_manager.is_exempt.return_value = False
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["status", "--json"])
        data = json.loads(result.stdout)
        assert data["active_violations"] == 1

    def test_status_baseline_exempt_not_counted(self):
        """Baseline-exempt violations excluded from active count."""
        container = self._mock_container()
        container.policy_parser.parse_rules.return_value = [
            Rule(id="r1", description="test")
        ]
        container.evaluation_service.evaluate_workspace.return_value = [
            ArchitecturalViolation(file="x.py", line=1, rule_id="r1", description="bad")
        ]
        container.baseline_manager.is_exempt.return_value = True
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["status", "--json"])
        data = json.loads(result.stdout)
        assert data["active_violations"] == 0

    def test_status_plugins_listed(self):
        """status shows loaded plugins."""
        container = self._mock_container()
        container.loaded_plugins = ["my-analyzer", "my-tool"]
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["status", "--json"])
        data = json.loads(result.stdout)
        assert data["plugins"] == ["my-analyzer", "my-tool"]

    def test_apply_no_violations(self, tmp_path):
        """apply reports clean when no active violations."""
        container = self._mock_container()
        rules_dir = os.path.join(str(tmp_path), ".aegis")
        os.makedirs(rules_dir, exist_ok=True)
        rules_file = os.path.join(rules_dir, "rules.yaml")
        with open(rules_file, "w", encoding="utf-8") as f:
            f.write("rules: []")
        container.workspace_root = str(tmp_path)
        container.policy_parser.parse_rules.return_value = []
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["apply"])
        assert "No active violations" in result.stdout

    def test_apply_with_violations(self, tmp_path):
        """apply generates remediation prompt for active violations."""
        container = self._mock_container()
        rules_dir = os.path.join(str(tmp_path), ".aegis")
        os.makedirs(rules_dir, exist_ok=True)
        rules_file = os.path.join(rules_dir, "rules.yaml")
        with open(rules_file, "w", encoding="utf-8") as f:
            f.write('rules: [{"id": "r1", "description": "test"}]')
        container.workspace_root = str(tmp_path)
        container.policy_parser.parse_rules.return_value = [
            Rule(id="r1", description="test")
        ]
        container.evaluation_service.evaluate_workspace.return_value = [
            ArchitecturalViolation(
                file="src/main.py", line=5, rule_id="r1", description="violation"
            )
        ]
        container.baseline_manager.is_exempt.return_value = False
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["apply"])
        assert "mock prompt" in result.stdout

    def test_apply_output_flag(self, tmp_path):
        """apply --output writes remediation prompt to file."""
        container = self._mock_container()
        rules_dir = os.path.join(str(tmp_path), ".aegis")
        os.makedirs(rules_dir, exist_ok=True)
        rules_file = os.path.join(rules_dir, "rules.yaml")
        with open(rules_file, "w", encoding="utf-8") as f:
            f.write('rules: [{"id": "r1", "description": "test"}]')
        container.workspace_root = str(tmp_path)
        container.policy_parser.parse_rules.return_value = [
            Rule(id="r1", description="test")
        ]
        container.evaluation_service.evaluate_workspace.return_value = [
            ArchitecturalViolation(
                file="src/main.py", line=5, rule_id="r1", description="violation"
            )
        ]
        container.baseline_manager.is_exempt.return_value = False
        out_file = str(tmp_path / "remediation.txt")
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["apply", "--output", out_file])
        assert "written to" in result.stdout
        with open(out_file, encoding="utf-8") as f:
            assert "mock prompt" in f.read()

    def test_evolve_prompts_for_input(self, tmp_path):
        """evolve interactively collects action + rationale and logs decision."""
        container = self._mock_container()
        rules_dir = os.path.join(str(tmp_path), ".aegis")
        os.makedirs(rules_dir, exist_ok=True)
        rules_file = os.path.join(rules_dir, "rules.yaml")
        with open(rules_file, "w", encoding="utf-8") as f:
            f.write('rules: [{"id": "r1", "description": "test"}]')
        container.workspace_root = str(tmp_path)
        container.policy_parser.parse_rules.return_value = [
            Rule(id="r1", description="test")
        ]
        cli = self._cli(container)
        result = runner.invoke(
            cli.app,
            ["evolve", "r1"],
            input="suppress\nlegacy debt\n",
        )
        assert result.exit_code == 0
        assert "Decision recorded" in result.stdout

    def test_evolve_unknown_rule(self, tmp_path):
        """evolve with nonexistent rule reports error."""
        container = self._mock_container()
        rules_dir = os.path.join(str(tmp_path), ".aegis")
        os.makedirs(rules_dir, exist_ok=True)
        rules_file = os.path.join(rules_dir, "rules.yaml")
        with open(rules_file, "w", encoding="utf-8") as f:
            f.write("rules: []")
        container.workspace_root = str(tmp_path)
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["evolve", "nonexistent"])
        assert "not found" in result.stdout

    def test_serve_help_shows_options(self):
        """serve --help shows transport/host/port options."""
        cli = self._cli()
        result = runner.invoke(cli.app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "transport" in result.stdout
        assert "stdio" in result.stdout
        assert "sse" in result.stdout

    def test_baseline_clear(self, tmp_path):
        """baseline --clear removes the baseline file."""
        container = self._mock_container()
        rules_dir = os.path.join(str(tmp_path), ".aegis")
        os.makedirs(rules_dir, exist_ok=True)
        baseline_path = os.path.join(rules_dir, "baseline.json")
        with open(baseline_path, "w", encoding="utf-8") as f:
            json.dump([{"file": "x.py", "line": 1, "rule_id": "r1"}], f)
        container.baseline_manager.path = baseline_path
        container.workspace_root = str(tmp_path)
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["baseline", "--clear"])
        assert result.exit_code == 0
        assert "Baseline cleared" in result.stdout
        assert not os.path.exists(baseline_path)

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
            f.write(
                'rules: [{"id": "r1", "description": "test", "severity": "HIGH", "mode": "block"}]'
            )
        container.workspace_root = str(tmp_path)
        container.policy_parser.parse_rules.return_value = [
            Rule(
                id="r1",
                description="test",
                severity=Severity.HIGH,
                mode=EnforcementMode.BLOCK,
            )
        ]
        container.evaluation_service.evaluate_workspace.return_value = [
            ArchitecturalViolation(
                file="src/main.py", line=1, rule_id="r1", description="test"
            )
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
            ArchitecturalViolation(
                file="src/main.py", line=1, rule_id="nonexistent", description="test"
            )
        ]
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["check"])
        assert result.exit_code == 0
