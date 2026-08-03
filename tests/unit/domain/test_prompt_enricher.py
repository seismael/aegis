"""Unit tests for aegis.domain.prompt_enricher."""

import pytest

from aegis.core.registry import EngineType, Rule, Severity


class TestEnrichPrompt:
    def test_enrich_prompt_returns_enriched_string(self, tmp_path):
        """Prompt includes the task and rules when rules exist."""
        from aegis.domain.prompt_enricher import enrich_prompt

        # Setup: deploy rules to tmp workspace
        rules_dir = tmp_path / ".aegis" / "rules" / "architecture"
        rules_dir.mkdir(parents=True)
        (rules_dir / "rules.yaml").write_text("""
rules:
  - id: arch-layer-violation
    description: Domain must not import infrastructure
    severity: HIGH
    mode: block
    engine_type: graph
    rationale: Layered architecture requires domain purity.
""")

        result = enrich_prompt(
            "Add email notifications",
            ["domain/services.py"],
            str(tmp_path),
        )

        assert "arch-layer-violation" in result
        assert "Add email notifications" in result
        assert "Layered architecture" in result

    def test_enrich_prompt_no_rules_raises(self, tmp_path):
        """Raises ValueError when workspace has no rules."""
        from aegis.domain.prompt_enricher import enrich_prompt

        (tmp_path / ".aegis").mkdir()
        with pytest.raises(ValueError, match="No rules found"):
            enrich_prompt("test", ["file.py"], str(tmp_path))

    def test_enrich_prompt_minimal_falls_back(self, tmp_path):
        """minimal version returns task unchanged if no rules."""
        from aegis.domain.prompt_enricher import enrich_prompt_minimal

        (tmp_path / ".aegis").mkdir()
        result = enrich_prompt_minimal("test", ["file.py"], str(tmp_path))
        assert result == "test"


class TestFormatRules:
    def test_format_rules_includes_severity_and_rationale(self):
        """Rule formatting includes all key fields."""
        from aegis.domain.prompt_enricher import _format_rules

        rule = Rule(
            id="test-rule",
            description="Test description",
            severity=Severity.HIGH,
            rationale="Important reason.",
            engine_type=EngineType.TREE_SITTER,
        )
        result = _format_rules([rule])

        assert "test-rule" in result
        assert "HIGH" in result
        assert "Test description" in result
        assert "Important reason" in result
        assert "tree-sitter" in result

    def test_format_rules_multiple_rules_separated(self):
        """Multiple rules are formatted with proper spacing."""
        from aegis.domain.prompt_enricher import _format_rules

        rules = [
            Rule(
                id="r1",
                description="D1",
                severity=Severity.HIGH,
                engine_type=EngineType.GRAPH,
            ),
            Rule(
                id="r2",
                description="D2",
                severity=Severity.MEDIUM,
                engine_type=EngineType.REGEX,
            ),
        ]
        result = _format_rules(rules)

        assert "r1 [HIGH]: D1" in result
        assert "r2 [MEDIUM]: D2" in result
