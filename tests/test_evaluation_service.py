from unittest.mock import MagicMock

from aegis.core.models.governance import Rule, Severity
from aegis.domain.evaluation.ports import (
    ArchitecturalViolation,
    DiffProviderInterface,
    DiffResult,
    GraphAnalyzerInterface,
    RegexAnalyzerInterface,
    RuleAnalyzerInterface,
)
from aegis.domain.evaluation.service import EvaluationService


class TestEvaluationService:
    """
    Test suite for the EvaluationService.
    """

    def _make_service(
        self,
        ts_analyzer=None,
        graph_analyzer=None,
        regex_analyzer=None,
        diff_provider=None,
    ):
        return EvaluationService(
            tree_sitter_analyzer=ts_analyzer or MagicMock(spec=RuleAnalyzerInterface),
            graph_analyzer=graph_analyzer or MagicMock(spec=GraphAnalyzerInterface),
            regex_analyzer=regex_analyzer or MagicMock(spec=RegexAnalyzerInterface),
            diff_provider=diff_provider or MagicMock(spec=DiffProviderInterface),
        )

    def test_evaluate_workspace(self, tmp_path):
        p = tmp_path / "src"
        p.mkdir()
        f1 = p / "main.py"
        f1.write_text("def f(): pass", encoding="utf-8")

        analyzer = MagicMock(spec=RuleAnalyzerInterface)
        analyzer.analyze_file.return_value = [
            ArchitecturalViolation(
                file=str(f1), line=1, rule_id="test-rule", description="error"
            )
        ]

        diff_provider = MagicMock(spec=DiffProviderInterface)
        graph_mock = MagicMock(spec=GraphAnalyzerInterface)
        regex_mock = MagicMock(spec=RegexAnalyzerInterface)

        service = EvaluationService(analyzer, graph_mock, regex_mock, diff_provider)
        rules = [
            Rule(
                id="test-rule",
                description="desc",
                query="query",
                severity=Severity.HIGH,
            )
        ]

        violations = service.evaluate_workspace(str(tmp_path), rules)
        assert len(violations) == 1
        assert violations[0].rule_id == "test-rule"

    def test_evaluate_changes(self):
        analyzer = MagicMock(spec=RuleAnalyzerInterface)
        analyzer.analyze_file.return_value = []

        diff_result = MagicMock(spec=DiffResult)
        diff_result.changed_files = {"src/main.py"}

        diff_provider = MagicMock(spec=DiffProviderInterface)
        diff_provider.get_staged_changes.return_value = diff_result

        graph_mock = MagicMock(spec=GraphAnalyzerInterface)
        regex_mock = MagicMock(spec=RegexAnalyzerInterface)

        service = EvaluationService(analyzer, graph_mock, regex_mock, diff_provider)

        try:
            service.evaluate_changes([])
        except FileNotFoundError:
            pass

        diff_provider.get_staged_changes.assert_called_once()
