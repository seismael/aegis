"""Integration tests: kernel, discovery, rule model, and full pipeline."""

import pytest

from aegis.domain.policy.models import EnforcementMode, Rule, Severity
from aegis.kernel.server import AegisKernel


class TestKernelComposition:
    """Kernel creation and project discovery."""

    def test_kernel_creates_without_crashing(self, tmp_path):
        """Kernel initializes successfully in a valid project dir."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        c = AegisKernel(workspace_root=str(tmp_path))
        assert c.workspace_root == str(tmp_path)
        assert c.policy is not None
        assert c.evaluation is not None
        assert c.baseline is not None
        assert c.packs is not None
        assert c.remediation is not None
        assert c.mcp is not None

    def test_discover_project_root_pyproject(self, tmp_path, monkeypatch):
        """_discover_root finds pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("")
        monkeypatch.chdir(tmp_path)
        c = AegisKernel()
        assert c.workspace_root == str(tmp_path)

    def test_discover_project_root_git(self, tmp_path, monkeypatch):
        """_discover_root finds .git directory."""
        (tmp_path / ".git").mkdir()
        monkeypatch.chdir(tmp_path)
        c = AegisKernel()
        assert c.workspace_root == str(tmp_path)

    def test_discover_project_root_fallback_cwd(self, tmp_path, monkeypatch):
        """_discover_root falls back to CWD when no markers found."""
        monkeypatch.chdir(tmp_path)
        
        # Mock Path.exists to return False so it simulates no markers found anywhere in the hierarchy
        from pathlib import Path
        original_exists = Path.exists
        monkeypatch.setattr(Path, "exists", lambda self: False)
        
        c = AegisKernel()
        assert c.workspace_root == str(tmp_path)


class TestRuleModelEdgeCases:
    """Rule model deserialization edge cases."""

    def test_rule_defaults(self):
        """Rule applies sensible defaults for optional fields."""
        r = Rule(id="r1", description="test")
        assert r.mode == EnforcementMode.BLOCK
        assert r.severity == Severity.HIGH
        assert r.query is None
        assert r.language == "python"
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


class TestFullPipeline:
    """End-to-end pipeline with temp workspace."""

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

        kernel = AegisKernel(workspace_root=str(tmp_path))

        rules = kernel._load_rules()
        violations = kernel.evaluation.evaluate_workspace(str(tmp_path), rules)
        assert len(violations) >= 1
        assert violations[0].rule_id == "no-todo"

        kernel.baseline.save_baseline(violations)
        baseline = kernel.baseline.load_baseline_raw()
        assert len(baseline) >= 1

        violations2 = kernel.evaluation.evaluate_workspace(str(tmp_path), rules)
        active = [v for v in violations2 if not kernel.baseline.is_exempt(v)]
        assert len(active) == 0

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

        kernel = AegisKernel(workspace_root=str(tmp_path))
        rules = kernel._load_rules()
        violations = kernel.evaluation.evaluate_workspace(str(tmp_path), rules)
        assert len(violations) >= 1

        kernel.baseline.save_baseline(violations)
        kernel2 = AegisKernel(workspace_root=str(tmp_path))
        violations2 = kernel2.evaluation.evaluate_workspace(str(tmp_path), rules)
        active = [v for v in violations2 if not kernel2.baseline.is_exempt(v)]
        assert len(active) == 0
