"""Integration tests: container, discovery, CLI flags, and full pipeline."""

import json

import pytest
from typer.testing import CliRunner

from aegis.cli.main import AegisCLI
from aegis.core.container.app import Container
from aegis.domain.policy.models import EnforcementMode, Rule, Severity

# ─── Container / DI composition ─────────────────────────────────────────────


class TestContainerComposition:
    """Cycle 6: DI container creation and project discovery."""

    def test_container_creates_without_crashing(self, tmp_path):
        """Container initializes successfully in a valid project dir."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        c = Container(workspace_root=str(tmp_path))
        assert c.workspace_root == str(tmp_path)
        assert c.policy_parser is not None
        assert c.evaluation_service is not None
        assert c.baseline_manager is not None
        assert c.evolution_service is not None
        assert c.remediation_synthesizer is not None
        assert c.plugin_registry is not None

    def test_discover_project_root_pyproject(self, tmp_path, monkeypatch):
        """_discover_project_root finds pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("")
        monkeypatch.chdir(tmp_path)
        c = Container()
        assert c.workspace_root == str(tmp_path)

    def test_discover_project_root_git(self, tmp_path, monkeypatch):
        """_discover_project_root finds .git directory."""
        (tmp_path / ".git").mkdir()
        monkeypatch.chdir(tmp_path)
        c = Container()
        assert c.workspace_root == str(tmp_path)

    def test_discover_project_root_fallback_cwd(self, tmp_path, monkeypatch):
        """_discover_project_root falls back to CWD when no markers found."""
        monkeypatch.chdir(tmp_path)
        c = Container()
        assert c.workspace_root == str(tmp_path)

    def test_container_loaded_plugins_property(self, tmp_path):
        """loaded_plugins property returns list from registry."""
        (tmp_path / "pyproject.toml").write_text("")
        c = Container(workspace_root=str(tmp_path))
        assert isinstance(c.loaded_plugins, list)

    def test_container_custom_mcp_tools_property(self, tmp_path):
        """custom_mcp_tools property returns list from registry."""
        (tmp_path / "pyproject.toml").write_text("")
        c = Container(workspace_root=str(tmp_path))
        assert isinstance(c.custom_mcp_tools, list)


# ─── CLI flag combinations ──────────────────────────────────────────────────


class TestCLIFlagCombinations:
    """Cycle 5: CLI check flag interactions."""

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
        c.remediation_synthesizer.generate_remediation.return_value = "mock prompt"
        c.governance_service = MagicMock()
        c.governance_service.get_active_violations.return_value = []
        c.governance_service.capture_baseline.return_value = 0
        return c

    def test_check_help_shows_flags(self):
        """check --help shows --staged, --rule, --strict flags."""
        cli = AegisCLI(container=self._mock_container())
        result = self.runner.invoke(cli.app, ["check", "--help"])
        assert "--staged" in result.stdout
        assert "--rule" in result.stdout
        assert "--strict" in result.stdout

    def test_check_strict_turns_warn_into_block(self, tmp_path):
        """--strict flag makes WARN-mode violations block (exit 1)."""
        from unittest.mock import MagicMock

        from aegis.domain.evaluation.ports import ArchitecturalViolation

        container = MagicMock()
        container.workspace_root = str(tmp_path)
        container.load_rules.return_value = [
            Rule(id="r1", description="test", mode=EnforcementMode.WARN)
        ]
        container.evaluation_service.evaluate_changes.return_value = []
        container.baseline_manager.is_exempt.return_value = False
        container.loaded_plugins = []
        container.remediation_synthesizer.generate_remediation.return_value = ""
        container.governance_service = MagicMock()
        container.governance_service.get_active_violations.return_value = [
            ArchitecturalViolation(
                file="x.py", line=1, rule_id="r1", description="test"
            )
        ]

        (tmp_path / ".aegis").mkdir()
        (tmp_path / ".aegis" / "rules.yaml").write_text("rules: []", encoding="utf-8")

        cli = AegisCLI(container=container)
        result = self.runner.invoke(cli.app, ["check", "--strict"])
        assert result.exit_code == 1

    def test_check_rule_filter_only_matching_rule(self, tmp_path):
        """--rule flag filters to a single rule."""
        from unittest.mock import MagicMock

        container = MagicMock()
        container.workspace_root = str(tmp_path)
        container.load_rules.return_value = [
            Rule(id="r1", description="test", mode=EnforcementMode.BLOCK),
            Rule(id="r2", description="test", mode=EnforcementMode.BLOCK),
        ]
        container.evaluation_service.evaluate_changes.return_value = []
        container.baseline_manager.is_exempt.return_value = False
        container.loaded_plugins = []
        container.remediation_synthesizer.generate_remediation.return_value = ""
        container.governance_service = MagicMock()
        container.governance_service.get_active_violations.return_value = []

        (tmp_path / ".aegis").mkdir()
        (tmp_path / ".aegis" / "rules.yaml").write_text("rules: []", encoding="utf-8")

        cli = AegisCLI(container=container)
        result = self.runner.invoke(cli.app, ["check", "--rule", "r1"])
        assert result.exit_code == 0  # No violations from filtered rule
        assert "Architecture compliant" in result.stdout


# ─── MCP server error handling ─────────────────────────────────────────────


class TestMCPErrorHandling:
    """Cycle 4: MCP tool error recovery."""

    @pytest.mark.asyncio
    async def test_validate_compliance_no_container(self):
        """validate_architecture_compliance returns error when container is None."""
        from aegis.kernel.server import AegisKernel

        k = AegisKernel()
        k.container = None
        result = await k.validate_architecture_compliance()
        assert "CONTAINER_NOT_INIT" in result

    @pytest.mark.asyncio
    async def test_apply_remediation_no_container(self):
        """apply_architectural_remediation returns error when container is None."""
        from aegis.kernel.server import AegisKernel

        k = AegisKernel()
        k.container = None
        result = await k.apply_architectural_remediation()
        assert "CONTAINER_NOT_INIT" in result

    @pytest.mark.asyncio
    async def test_get_rule_rationale_no_container(self):
        """get_rule_rationale warns when rule not found (container=None fallback)."""
        from aegis.kernel.server import AegisKernel

        k = AegisKernel()
        k.container = None
        result = await k.get_rule_rationale("r1")
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_server_status_degraded(self):
        """server_status reports degraded when container is None."""
        from aegis.kernel.server import AegisKernel

        k = AegisKernel()
        k.container = None
        result = await k.server_status()
        assert "degraded" in result

    @pytest.mark.asyncio
    async def test_get_dependency_graph_no_modules(self):
        """get_dependency_graph warns when no Python modules found."""
        from unittest.mock import MagicMock

        from aegis.kernel.server import AegisKernel

        k = AegisKernel()
        mock_container = MagicMock()
        mock_container.workspace_root = "/empty/dir"
        mock_container.graph_analyzer = MagicMock()
        mock_container.graph_analyzer.build_import_graph.return_value = ({}, {})
        k.container = mock_container
        result = await k.get_dependency_graph("main")
        assert '"success": false' in result
        assert "No Python modules found" in result


# ─── Rule model deserialization ────────────────────────────────────────────


class TestRuleModelEdgeCases:
    """Cycle 8: Rule model deserialization edge cases."""

    def test_rule_defaults(self):
        """Rule applies sensible defaults for optional fields."""
        r = Rule(id="r1", description="test")
        assert r.mode == EnforcementMode.BLOCK
        assert r.severity == Severity.HIGH
        assert r.query is None
        assert r.language == "py"
        assert r.rationale is None

    def test_rule_deserialize_minimal(self):
        """Rule can be deserialized from minimal dict."""
        data = {"id": "r1", "description": "test rule"}
        r = Rule.model_validate(data)
        assert r.id == "r1"
        assert r.description == "test rule"

    def test_rule_deserialize_full(self):
        """Rule can be deserialized with all fields."""
        data = {
            "id": "r1",
            "description": "test",
            "severity": "CRITICAL",
            "mode": "warn",
            "engine_type": "regex",
            "query": r"TODO",
            "language": "py",
            "rationale": "Keep code clean.",
            "applies_to": ["src/**"],
            "excludes": ["tests/**"],
            "metadata": {"key": "value"},
        }
        r = Rule.model_validate(data)
        assert r.severity == Severity.CRITICAL
        assert r.mode == EnforcementMode.WARN
        assert r.engine_type.value == "regex"
        assert r.rationale == "Keep code clean."
        assert r.applies_to == ["src/**"]

    def test_rule_unknown_enum_fallback(self):
        """Unknown enum values raise validation error (fail fast)."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Rule.model_validate(
                {"id": "r1", "description": "test", "severity": "INVALID"}
            )

    def test_rule_missing_id_raises(self):
        """Rule without id field raises validation error."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="id"):
            Rule.model_validate({"description": "test"})

    def test_rule_missing_description_raises(self):
        """Rule without description raises validation error."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="description"):
            Rule.model_validate({"id": "r1"})


# ─── Full pipeline E2E ─────────────────────────────────────────────────────


class TestFullPipeline:
    """Cycle 10: End-to-end pipeline with temp workspace."""

    def test_full_pipeline_evaluate_and_baseline(self, tmp_path):
        """Full cycle: create rules -> evaluate -> baseline -> re-evaluate exempt."""
        aegis_dir = tmp_path / ".aegis"
        rules_dir = aegis_dir / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "architecture.yaml").write_text(
            "rules:\n  - id: no-todo\n    description: No TODOs\n"
            "    query: TODO\n"
            "    engine_type: regex\n    severity: HIGH\n    mode: block\n",
            encoding="utf-8",
        )
        src_file = tmp_path / "main.py"
        src_file.write_text("# TODO: implement this\nx = 1\n", encoding="utf-8")

        container = Container(workspace_root=str(tmp_path))

        # Step 1: Evaluate
        rules = container.load_rules()
        violations = container.evaluation_service.evaluate_workspace(
            str(tmp_path), rules
        )
        assert len(violations) >= 1
        assert violations[0].rule_id == "no-todo"

        # Step 2: Baseline
        container.baseline_manager.save_baseline(violations)
        baseline = container.baseline_manager.load_baseline_raw()
        assert len(baseline) >= 1

        # Step 3: Re-evaluate — violations should be exempt
        violations2 = container.evaluation_service.evaluate_workspace(
            str(tmp_path), rules
        )
        active = [v for v in violations2 if not container.baseline_manager.is_exempt(v)]
        assert len(active) == 0

    def test_full_pipeline_cli_check(self, tmp_path):
        """CLI check --json works end-to-end against real workspace."""
        aegis_dir = tmp_path / ".aegis"
        rules_dir = aegis_dir / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "architecture.yaml").write_text(
            "rules:\n  - id: no-todo\n    description: No TODOs\n    query: TODO\n",
            encoding="utf-8",
        )
        (tmp_path / "app.py").write_text("# TODO: fix\n", encoding="utf-8")

        container = Container(workspace_root=str(tmp_path))
        cli = AegisCLI(container=container)
        runner = CliRunner()
        result = runner.invoke(cli.app, ["status", "--json"])
        assert result.exit_code == 0
        # Strip any log lines before the JSON
        stdout = result.stdout
        json_start = stdout.index("{")
        data = json.loads(stdout[json_start:])
        assert "rules" in data
        assert "engines" in data
        assert data["rules_count"] >= 1

    def test_pipeline_apply_then_baseline(self, tmp_path):
        """Apply detects violations, baseline suppresses them."""
        aegis_dir = tmp_path / ".aegis"
        rules_dir = aegis_dir / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "architecture.yaml").write_text(
            "rules:\n  - id: no-todo\n    description: No TODOs\n"
            "    query: TODO\n"
            "    engine_type: regex\n    severity: HIGH\n    mode: block\n",
            encoding="utf-8",
        )
        (tmp_path / "app.py").write_text(
            "# TODO: implement me\ndef foo(): pass\n",
            encoding="utf-8",
        )

        container = Container(workspace_root=str(tmp_path))
        rules = container.load_rules()
        violations = container.evaluation_service.evaluate_workspace(
            str(tmp_path), rules
        )
        assert len(violations) >= 1

        # Baseline the violations
        container.baseline_manager.save_baseline(violations)
        container2 = Container(workspace_root=str(tmp_path))
        violations2 = container2.evaluation_service.evaluate_workspace(
            str(tmp_path), rules
        )
        active = [
            v for v in violations2 if not container2.baseline_manager.is_exempt(v)
        ]
        assert len(active) == 0
