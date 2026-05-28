import pytest
from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.evaluation.service import EvaluationService
from aegis.domain.policy.models import Rule, EngineType, Severity, EnforcementMode
from unittest.mock import MagicMock

def test_proposed_patch_in_violation():
    violation = ArchitecturalViolation(
        file="test.py",
        line=1,
        rule_id="test-rule",
        description="test violation",
        proposed_patch="--- test.py\n+++ test.py\n@@ -1 +1 @@\n-print('bad')\n+print('good')"
    )
    assert violation.proposed_patch is not None
    assert "print('good')" in violation.proposed_patch

def test_suggested_replacement_in_rule():
    rule = Rule(
        id="test-rule",
        description="test rule",
        engine_type=EngineType.REGEX,
        query="bad",
        metadata={"suggested_replacement": "good"}
    )
    assert rule.metadata["suggested_replacement"] == "good"

def test_evaluation_service_generates_diff():
    # This test will likely fail until we implement the logic
    ts_analyzer = MagicMock()
    graph_analyzer = MagicMock()
    regex_analyzer = MagicMock()
    
    service = EvaluationService(
        tree_sitter_analyzer=ts_analyzer,
        graph_analyzer=graph_analyzer,
        regex_analyzer=regex_analyzer
    )
    
    rule = Rule(
        id="no-print",
        description="No print statements",
        engine_type=EngineType.REGEX,
        query="print\((.*?)\)",
        metadata={"suggested_replacement": "logger.info(\\1)"}
    )
    
    content = "print('hello')"
    file_path = "app.py"
    
    # Mock regex_analyzer to return a violation without patch
    regex_analyzer.analyze_file.return_value = [
        ArchitecturalViolation(
            file=file_path,
            line=1,
            rule_id=rule.id,
            description=rule.description
        )
    ]
    
    with open(file_path, "w") as f:
        f.write(content)
        
    try:
        violations = service.evaluate_file(file_path, [rule])
        assert len(violations) == 1
        # We want the service to enrich the violation with a proposed_patch if it can
        assert violations[0].proposed_patch is not None
        assert "logger.info('hello')" in violations[0].proposed_patch
    finally:
        import os
        if os.path.exists(file_path):
            os.remove(file_path)
