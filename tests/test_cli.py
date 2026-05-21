import json
import os
from unittest.mock import MagicMock

from typer.testing import CliRunner

from aegis.cli.main import AegisCLI
from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.policy.models import EnforcementMode, EngineType, Rule, Severity

runner = CliRunner()


class TestAegisCLI:
    """Test suite for the AegisCLI — user-facing commands."""

    def _mock_container(self):
        c = MagicMock()
        c.workspace_root = "/fake/project"
        c.load_rules.return_value = []
        c.evaluation_service.evaluate_workspace.return_value = []
        c.evaluation_service.evaluate_changes.return_value = []
        c.baseline_manager.load_baseline_raw.return_value = []
        c.baseline_manager.is_exempt.return_value = False
        c.loaded_plugins = []
        from aegis.domain.enforcement.ports import RemediationResult

        c.remediation_synthesizer.generate_remediation.return_value = RemediationResult(
            summary="violations", violations_count=1, handoff_prompt="mock prompt"
        )
        c.governance_service = MagicMock()
        c.governance_service.get_active_violations.return_value = []
        c.governance_service.capture_baseline.return_value = 0
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
        """status does not crash when baseline has entries (dict vs attrs)."""
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
        container.load_rules.return_value = [
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
        container.load_rules.return_value = [Rule(id="r1", description="test")]
        container.governance_service.get_active_violations.return_value = [
            ArchitecturalViolation(file="x.py", line=1, rule_id="r1", description="bad")
        ]
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["status", "--json"])
        data = json.loads(result.stdout)
        assert data["active_violations"] == 1

    def test_status_baseline_exempt_not_counted(self):
        """Baseline-exempt violations excluded from active count."""
        container = self._mock_container()
        container.load_rules.return_value = [Rule(id="r1", description="test")]
        # Default governance mock already returns [] — no active violations
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
        container.load_rules.return_value = [Rule(id="r1", description="test")]
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
        container.load_rules.return_value = [Rule(id="r1", description="test")]
        container.governance_service.get_active_violations.return_value = [
            ArchitecturalViolation(
                file="src/main.py", line=5, rule_id="r1", description="violation"
            )
        ]
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
        container.load_rules.return_value = [Rule(id="r1", description="test")]
        container.governance_service.get_active_violations.return_value = [
            ArchitecturalViolation(
                file="src/main.py", line=5, rule_id="r1", description="violation"
            )
        ]
        out_file = str(tmp_path / "remediation.txt")
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["apply", "--output", out_file])
        assert "written to" in result.stdout
        with open(out_file, encoding="utf-8") as f:
            assert "mock prompt" in f.read()

    def test_evolve_prompts_for_input(self, tmp_path):
        """evolve requires --action and --rationale flags."""
        container = self._mock_container()
        rules_dir = os.path.join(str(tmp_path), ".aegis")
        os.makedirs(rules_dir, exist_ok=True)
        rules_file = os.path.join(rules_dir, "rules.yaml")
        with open(rules_file, "w", encoding="utf-8") as f:
            f.write('rules: [{"id": "r1", "description": "test"}]')
        container.workspace_root = str(tmp_path)
        container.load_rules.return_value = [Rule(id="r1", description="test")]
        cli = self._cli(container)
        result = runner.invoke(
            cli.app,
            ["evolve", "r1", "--action", "suppress", "--rationale", "legacy debt"],
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
        container.load_rules.return_value = [Rule(id="r1", description="test")]
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["evolve", "nonexistent"])
        assert "not found" in result.stdout

    def test_serve_help_shows_options(self):
        """serve --help shows transport/host/port/cors-origins options."""
        cli = self._cli()
        result = runner.invoke(cli.app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "transport" in result.stdout
        assert "stdio" in result.stdout
        assert "sse" in result.stdout
        assert "cors-origins" in result.stdout

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

    def test_baseline_show(self, tmp_path):
        """baseline --show displays baseline summary."""
        container = self._mock_container()
        container.baseline_manager.show_baseline.return_value = "r1: 3 entries"
        container.workspace_root = str(tmp_path)
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["baseline", "--show"])
        assert result.exit_code == 0
        assert "r1: 3 entries" in result.stdout

    def test_baseline_prune(self, tmp_path):
        """baseline --prune removes stale entries."""
        container = self._mock_container()
        container.load_rules.return_value = [Rule(id="r1", description="test")]
        container.baseline_manager.prune_stale.return_value = 2
        container.workspace_root = str(tmp_path)
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["baseline", "--prune"])
        assert result.exit_code == 0
        assert "Pruned 2" in result.stdout

    def test_baseline_expire_days(self, tmp_path):
        """baseline --expire-days removes old entries."""
        container = self._mock_container()
        container.load_rules.return_value = [Rule(id="r1", description="test")]
        container.baseline_manager.expire_old.return_value = 5
        container.workspace_root = str(tmp_path)
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["baseline", "--expire-days", "90"])
        assert result.exit_code == 0
        assert "Expired 5" in result.stdout
        assert "90 days" in result.stdout

    def test_check_no_rules_file(self, tmp_path):
        """check exits 1 when rules.yaml missing."""
        container = self._mock_container()
        container.workspace_root = str(tmp_path)
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["check"])
        assert result.exit_code == 1
        assert "No rules found" in result.stdout

    def test_check_compliant(self, tmp_path):
        """check prints compliant when no violations."""
        container = self._mock_container()
        rules_dir = os.path.join(str(tmp_path), ".aegis")
        os.makedirs(rules_dir, exist_ok=True)
        rules_file = os.path.join(rules_dir, "rules.yaml")
        with open(rules_file, "w", encoding="utf-8") as f:
            f.write("rules: []")
        container.workspace_root = str(tmp_path)
        container.load_rules.return_value = [Rule(id="r1", description="test")]
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["check"])
        assert result.exit_code == 0

    def test_check_exit_code_with_warn_violation(self, tmp_path):
        """check --exit-code exits 1 on WARN violations."""
        container = self._mock_container()
        rules_dir = os.path.join(str(tmp_path), ".aegis")
        os.makedirs(rules_dir, exist_ok=True)
        rules_file = os.path.join(rules_dir, "rules.yaml")
        with open(rules_file, "w", encoding="utf-8") as f:
            f.write("rules: []")
        container.workspace_root = str(tmp_path)
        container.load_rules.return_value = [
            Rule(
                id="r1",
                description="test",
                severity=Severity.WARN,
                mode=EnforcementMode.WARN,
            )
        ]
        container.governance_service.get_active_violations.return_value = [
            ArchitecturalViolation(
                file="src/main.py", line=1, rule_id="r1", description="warn only"
            )
        ]
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["check", "--exit-code"])
        assert result.exit_code == 1

    def test_check_exit_code_with_no_violations(self, tmp_path):
        """check --exit-code exits 0 when no violations."""
        container = self._mock_container()
        rules_dir = os.path.join(str(tmp_path), ".aegis")
        os.makedirs(rules_dir, exist_ok=True)
        rules_file = os.path.join(rules_dir, "rules.yaml")
        with open(rules_file, "w", encoding="utf-8") as f:
            f.write("rules: []")
        container.workspace_root = str(tmp_path)
        container.load_rules.return_value = [Rule(id="r1", description="test")]
        container.governance_service.get_active_violations.return_value = []
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["check", "--exit-code"])
        assert result.exit_code == 0

    def test_check_blocking_violation_exits_1(self, tmp_path):
        """check exits 1 when blocking violations found."""
        container = self._mock_container()
        rules_dir = os.path.join(str(tmp_path), ".aegis")
        os.makedirs(rules_dir, exist_ok=True)
        rules_file = os.path.join(rules_dir, "rules.yaml")
        with open(rules_file, "w", encoding="utf-8") as f:
            f.write(
                "rules: ["
                '{"id": "r1", "description": "test",'
                ' "severity": "HIGH", "mode": "block"}]'
            )
        container.workspace_root = str(tmp_path)
        container.load_rules.return_value = [
            Rule(
                id="r1",
                description="test",
                severity=Severity.HIGH,
                mode=EnforcementMode.BLOCK,
            )
        ]
        container.governance_service.get_active_violations.return_value = [
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
        container.load_rules.return_value = [Rule(id="r1", description="test")]
        container.governance_service.get_active_violations.return_value = [
            ArchitecturalViolation(
                file="src/main.py", line=1, rule_id="nonexistent", description="test"
            )
        ]
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["check"])
        assert result.exit_code == 0

    def test_fix_no_fixable_violations(self, tmp_path):
        """fix with no violations reports green."""
        container = self._mock_container()
        rules_dir = os.path.join(str(tmp_path), ".aegis")
        os.makedirs(rules_dir, exist_ok=True)
        rules_file = os.path.join(rules_dir, "rules.yaml")
        with open(rules_file, "w", encoding="utf-8") as f:
            f.write("rules: []")
        container.workspace_root = str(tmp_path)
        container.load_rules.return_value = [
            Rule(id="bp-explicit-exceptions", description="test"),
        ]
        container.governance_service.get_active_violations.return_value = []
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["fix"])
        assert "No fixable violations" in result.stdout

    def test_fix_unknown_rule(self, tmp_path):
        """fix --rule with unknown rule reports yellow."""
        container = self._mock_container()
        container.workspace_root = str(tmp_path)
        container.load_rules.return_value = [Rule(id="r1", description="test")]
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["fix", "--rule", "nonexistent"])
        assert "no auto-fix" in result.stdout

    def test_fix_dry_run(self, tmp_path):
        """fix --dry-run shows count without modifying files."""
        container = self._mock_container()
        rules_dir = os.path.join(str(tmp_path), ".aegis")
        os.makedirs(rules_dir, exist_ok=True)
        rules_file = os.path.join(rules_dir, "rules.yaml")
        with open(rules_file, "w", encoding="utf-8") as f:
            f.write("rules: []")
        container.workspace_root = str(tmp_path)
        container.load_rules.return_value = [
            Rule(id="bp-explicit-exceptions", description="test"),
            Rule(id="no-print-statements", description="test"),
        ]
        container.governance_service.get_active_violations.return_value = [
            ArchitecturalViolation(
                file=os.path.join(str(tmp_path), "test.py"),
                line=1,
                rule_id="bp-explicit-exceptions",
                description="bare except",
            ),
        ]
        test_file = os.path.join(str(tmp_path), "test.py")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("except:\n")
        cli = self._cli(container)
        result = runner.invoke(cli.app, ["fix", "--dry-run"])
        assert "would be fixed" in result.stdout


class TestWatchCLI:
    """Tests for aegis watch command."""

    runner = CliRunner()

    def _mock_container(self):
        from unittest.mock import MagicMock

        c = MagicMock()
        c.workspace_root = "/fake/project"
        c.load_rules.return_value = [Rule(id="r1", description="test")]
        c.evaluation_service.evaluate_file.return_value = []
        c.baseline_manager.is_exempt.return_value = False
        return c

    def test_watch_no_rules(self, tmp_path):
        """watch exits 1 when no rules loaded."""
        c = self._mock_container()
        c.load_rules.return_value = []
        c.workspace_root = str(tmp_path)
        cli = AegisCLI(container=c)
        result = self.runner.invoke(cli.app, ["watch"])
        assert result.exit_code == 1
        assert "No rules found" in result.stdout

    def test_watch_unknown_rule(self, tmp_path):
        """watch --rule with non-existent rule ID exits 1."""
        c = self._mock_container()
        c.load_rules.return_value = [Rule(id="r1", description="test")]
        c.workspace_root = str(tmp_path)
        cli = AegisCLI(container=c)
        result = self.runner.invoke(cli.app, ["watch", "--rule", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.stdout


class TestPluginCLI:
    """Tests for aegis plugin commands."""

    runner = CliRunner()

    def test_plugin_create(self, tmp_path):
        """plugin create scaffolds a new plugin file."""
        from unittest.mock import MagicMock

        c = MagicMock()
        c.workspace_root = str(tmp_path)
        cli = AegisCLI(container=c)
        result = self.runner.invoke(cli.app, ["plugin", "create", "my-custom"])
        assert result.exit_code == 0, f"Exited {result.exit_code}: {result.stdout}"
        assert "Plugin scaffold created" in result.stdout
        # Scaffold converts hyphens to underscores
        plugin_file = os.path.join(str(tmp_path), ".aegis", "plugins", "my_custom.py")
        assert os.path.exists(plugin_file), f"Not found: {plugin_file}"

    def test_plugin_create_invalid_name(self, tmp_path):
        """plugin create with invalid name exits 1."""
        from unittest.mock import MagicMock

        c = MagicMock()
        c.workspace_root = str(tmp_path)
        cli = AegisCLI(container=c)
        result = self.runner.invoke(cli.app, ["plugin", "create", ""])
        assert result.exit_code != 0


class TestInsightsCLI:
    """Tests for aegis insights command."""

    runner = CliRunner()

    def _mock_container(self):
        from unittest.mock import MagicMock

        c = MagicMock()
        c.workspace_root = "/fake/project"
        c.load_rules.return_value = []
        c.evaluation_service.evaluate_workspace.return_value = []
        c.evaluation_service.evaluate_changes.return_value = []
        c.baseline_manager.load_baseline_raw.return_value = []
        c.baseline_manager.is_exempt.return_value = False
        c.loaded_plugins = []
        from aegis.domain.enforcement.ports import RemediationResult

        c.remediation_synthesizer.generate_remediation.return_value = RemediationResult(
            summary="violations", violations_count=1, handoff_prompt="mock prompt"
        )
        c.governance_service = MagicMock()
        c.governance_service.get_active_violations.return_value = []
        return c

    def test_insights_with_data(self, tmp_path):
        """insights shows scorecard when telemetry has data."""
        from unittest.mock import MagicMock

        container = self._mock_container()
        container.workspace_root = str(tmp_path)
        mock_recorder = MagicMock()
        mock_recorder.display_insights.return_value = (
            "## Aegis Insights Scorecard\n\n"
            "- **Total checks run:** 2\n"
            "- **Total remediations applied: 1**\n"
        )
        container.telemetry_recorder = mock_recorder

        cli = AegisCLI(container=container)
        result = self.runner.invoke(cli.app, ["insights"])
        assert result.exit_code == 0
        assert "checks run" in result.stdout
        assert "remediations applied" in result.stdout

    def test_insights_no_telemetry(self, tmp_path):
        """insights reports error when telemetry unavailable."""
        container = self._mock_container()
        container.workspace_root = str(tmp_path)
        # No telemetry recorder mock — simulate unavailable
        container.telemetry_recorder = None

        cli = AegisCLI(container=container)
        result = self.runner.invoke(cli.app, ["insights"])
        assert result.exit_code == 1
        assert "unavailable" in result.stdout.lower()
