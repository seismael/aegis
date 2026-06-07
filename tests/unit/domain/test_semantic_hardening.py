from unittest.mock import MagicMock

import pytest

from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.policy.models import EngineType, Rule, RuleCategory, Severity
from aegis.kernel.server import AegisKernel


@pytest.mark.asyncio
async def test_check_architecture_with_semantic_rules():
    # Setup
    kernel = AegisKernel(workspace_root="/tmp/fake")

    # Mock dependencies
    kernel.policy = MagicMock()
    kernel.evaluation = MagicMock()
    kernel.baseline = MagicMock()
    kernel.remediation = MagicMock()
    kernel.semantic = MagicMock()

    # Create a semantic rule
    semantic_rule = Rule(
        id="sem-1",
        description="No PII logged",
        engine_type=EngineType.SEMANTIC,
        category=RuleCategory.SECURITY,
        severity=Severity.HIGH,
    )

    kernel.policy.parse_all.return_value = [semantic_rule]
    kernel._filter_rules_for_files = MagicMock(return_value=[semantic_rule])
    kernel.evaluation.evaluate_workspace.return_value = []  # No structural violations
    kernel.baseline.is_exempt.return_value = False

    # Mock rubric generation
    kernel.semantic.build_rubric.return_value = (
        "### 🧩 Semantic Grading Rubric for `test.py`\nIntent: No PII logged"
    )

    # Execution
    result = await kernel.check_architecture(files_modified=["test.py"])

    # Verification
    assert "🧠 Re-entrant Semantic Evaluation Required" in result
    assert "sem-1" in result or "No PII logged" in result
    assert "SUCCESS" not in result
    kernel.semantic.build_rubric.assert_called_once()


@pytest.mark.asyncio
async def test_check_architecture_with_both_violations():
    # Setup
    kernel = AegisKernel(workspace_root="/tmp/fake")

    # Mock dependencies
    kernel.policy = MagicMock()
    kernel.evaluation = MagicMock()
    kernel.baseline = MagicMock()
    kernel.remediation = MagicMock()
    kernel.semantic = MagicMock()

    # Create rules
    semantic_rule = Rule(
        id="sem-1",
        description="No PII logged",
        engine_type=EngineType.SEMANTIC,
        category=RuleCategory.SECURITY,
        severity=Severity.HIGH,
    )
    regex_rule = Rule(
        id="reg-1",
        description="No print statements",
        engine_type=EngineType.REGEX,
        category=RuleCategory.STYLE,
        severity=Severity.MEDIUM,
    )

    kernel.policy.parse_all.return_value = [semantic_rule, regex_rule]
    kernel._filter_rules_for_files = MagicMock(return_value=[semantic_rule, regex_rule])

    # Structural violation
    violation = ArchitecturalViolation(
        file="test.py", line=1, rule_id="reg-1", description="Found print"
    )
    kernel.evaluation.evaluate_workspace.return_value = [violation]
    kernel.baseline.is_exempt.return_value = False

    # Mock remediation
    remediation_result = MagicMock()
    remediation_result.handoff_prompt = "## Structural Violations\n- reg-1: Found print"
    kernel.remediation.generate_remediation.return_value = remediation_result

    # Mock rubric generation
    kernel.semantic.build_rubric.return_value = (
        "### 🧩 Semantic Grading Rubric for `test.py`"
    )

    # Execution
    result = await kernel.check_architecture(files_modified=["test.py"])

    # Verification
    assert "## Structural Violations" in result
    assert "🧠 Re-entrant Semantic Evaluation Required" in result
    assert "SUCCESS" not in result


def test_semantic_analyzer_heuristic():
    from aegis.domain.evaluation.analyzers.semantic import SemanticAnalyzer

    analyzer = SemanticAnalyzer()
    rule = Rule(
        id="sem-pii",
        description="No PII",
        engine_type=EngineType.SEMANTIC,
        metadata={"sim_triggers": ["email", "ssn"]},
    )

    # Violation
    violations = analyzer.analyze_semantic(
        "test.py", "log_info('user email is test@example.com')", [rule]
    )
    assert len(violations) == 1
    assert "POTENTIAL SEMANTIC VIOLATION" in violations[0].description
    assert "email" in violations[0].description

    # No violation
    violations = analyzer.analyze_semantic("test.py", "log_info('all good')", [rule])
    assert len(violations) == 0


def test_semantic_analyzer_build_rubric():
    from aegis.domain.evaluation.analyzers.semantic import SemanticAnalyzer

    analyzer = SemanticAnalyzer()
    rule = Rule(
        id="sem-pii",
        description="No PII logged",
        engine_type=EngineType.SEMANTIC,
        severity=Severity.HIGH,
    )

    rubric = analyzer.build_rubric("test.py", [rule])
    assert "🧩 Semantic Grading Rubric for `test.py`" in rubric
    assert "sem-pii" in rubric
    assert "No PII logged" in rubric
    assert "Instructions for Agent-Native Self-Evaluation" in rubric
