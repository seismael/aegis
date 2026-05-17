import pytest
from unittest.mock import MagicMock
from aegis.domain.evaluation.service import EvaluationService
from aegis.core.models.governance import Rule, Severity
from aegis.domain.evaluation.ports import ASTAnalyzerInterface, ASTViolation, DiffProviderInterface, DiffResult

class TestEvaluationService:
    """
    Test suite for the EvaluationService.
    """
    def test_evaluate_workspace(self, tmp_path):
        # Setup mock files
        p = tmp_path / "src"
        p.mkdir()
        f1 = p / "main.py"
        f1.write_text("def f(): pass", encoding="utf-8")
        
        analyzer = MagicMock(spec=ASTAnalyzerInterface)
        analyzer.analyze_file.return_value = [
            ASTViolation(file=str(f1), line=1, rule_id="test-rule", description="error")
        ]
        
        diff_provider = MagicMock(spec=DiffProviderInterface)
        
        service = EvaluationService(analyzer, diff_provider)
        rules = [Rule(id="test-rule", description="desc", query="query", severity=Severity.HIGH)]
        
        violations = service.evaluate_workspace(str(tmp_path), rules)
        
        assert len(violations) == 1
        assert violations[0].rule_id == "test-rule"

    def test_evaluate_changes(self):
        analyzer = MagicMock(spec=ASTAnalyzerInterface)
        analyzer.analyze_file.return_value = []
        
        diff_result = MagicMock(spec=DiffResult)
        diff_result.changed_files = {"src/main.py"}
        
        diff_provider = MagicMock(spec=DiffProviderInterface)
        diff_provider.get_staged_changes.return_value = diff_result
        
        service = EvaluationService(analyzer, diff_provider)
        
        try:
            service.evaluate_changes([])
        except FileNotFoundError:
            pass
            
        diff_provider.get_staged_changes.assert_called_once()
