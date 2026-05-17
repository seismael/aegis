from unittest.mock import MagicMock

from aegis.core.models.governance import EngineType, Rule, Severity
from aegis.domain.evaluation.ports import (
    RuleAnalyzerInterface,
    DiffProviderInterface,
    GraphAnalyzerInterface,
    RegexAnalyzerInterface,
)
from aegis.domain.evaluation.service import EvaluationService


class TestEvaluationRouting:
    """
    Test suite for multi-engine routing in EvaluationService.
    """

    def _make_mocks(self):
        return (
            MagicMock(spec=RuleAnalyzerInterface),
            MagicMock(spec=GraphAnalyzerInterface),
            MagicMock(spec=RegexAnalyzerInterface),
            MagicMock(spec=DiffProviderInterface),
        )

    def _make_service(self, ts, graph, regex, diff):
        return EvaluationService(ts, graph, regex, diff)

    def test_tree_sitter_rules_dispatched_to_ts_analyzer(self, tmp_path):
        ts_mock, graph_mock, regex_mock, diff_mock = self._make_mocks()
        ts_mock.analyze_file.return_value = []
        graph_mock.analyze_graph.return_value = []
        regex_mock.analyze_file.return_value = []

        p = tmp_path / "src"
        p.mkdir()
        f = p / "main.py"
        f.write_text("x = 1", encoding="utf-8")

        service = self._make_service(ts_mock, graph_mock, regex_mock, diff_mock)
        rules = [
            Rule(
                id="ts-rule",
                description="Tree-sitter rule",
                engine_type=EngineType.TREE_SITTER,
                severity=Severity.HIGH,
            )
        ]
        service.evaluate_workspace(str(tmp_path), rules)
        ts_mock.analyze_file.assert_called_once()
        graph_mock.analyze_graph.assert_not_called()
        regex_mock.analyze_file.assert_not_called()

    def test_graph_rules_dispatched_to_graph_analyzer(self, tmp_path):
        ts_mock, graph_mock, regex_mock, diff_mock = self._make_mocks()
        ts_mock.analyze_file.return_value = []
        graph_mock.analyze_graph.return_value = []
        regex_mock.analyze_file.return_value = []

        service = self._make_service(ts_mock, graph_mock, regex_mock, diff_mock)
        rules = [
            Rule(
                id="graph-rule",
                description="Graph rule",
                engine_type=EngineType.GRAPH,
                severity=Severity.HIGH,
            )
        ]
        service.evaluate_workspace(str(tmp_path), rules)
        graph_mock.analyze_graph.assert_called_once()
        ts_mock.analyze_file.assert_not_called()
        regex_mock.analyze_file.assert_not_called()

    def test_regex_rules_dispatched_to_regex_analyzer(self, tmp_path):
        ts_mock, graph_mock, regex_mock, diff_mock = self._make_mocks()
        ts_mock.analyze_file.return_value = []
        graph_mock.analyze_graph.return_value = []
        regex_mock.analyze_file.return_value = []

        p = tmp_path / "src"
        p.mkdir()
        f = p / "main.py"
        f.write_text("x = 1", encoding="utf-8")

        service = self._make_service(ts_mock, graph_mock, regex_mock, diff_mock)
        rules = [
            Rule(
                id="regex-rule",
                description="Regex rule",
                engine_type=EngineType.REGEX,
                severity=Severity.HIGH,
            )
        ]
        service.evaluate_workspace(str(tmp_path), rules)
        regex_mock.analyze_file.assert_called_once()
        ts_mock.analyze_file.assert_not_called()
        graph_mock.analyze_graph.assert_not_called()

    def test_mixed_routes_when_multiple_engine_types(self, tmp_path):
        ts_mock, graph_mock, regex_mock, diff_mock = self._make_mocks()
        ts_mock.analyze_file.return_value = []
        graph_mock.analyze_graph.return_value = []
        regex_mock.analyze_file.return_value = []

        p = tmp_path / "src"
        p.mkdir()
        f = p / "main.py"
        f.write_text("x = 1", encoding="utf-8")

        service = self._make_service(ts_mock, graph_mock, regex_mock, diff_mock)
        rules = [
            Rule(
                id="ts",
                description="TS",
                engine_type=EngineType.TREE_SITTER,
                severity=Severity.HIGH,
            ),
            Rule(
                id="gr",
                description="GR",
                engine_type=EngineType.GRAPH,
                severity=Severity.HIGH,
            ),
            Rule(
                id="re",
                description="RE",
                engine_type=EngineType.REGEX,
                severity=Severity.HIGH,
            ),
        ]
        service.evaluate_workspace(str(tmp_path), rules)
        ts_mock.analyze_file.assert_called_once()
        graph_mock.analyze_graph.assert_called_once()
        regex_mock.analyze_file.assert_called_once()

    def test_graph_rules_skipped_in_evaluate_changes(self):
        ts_mock, graph_mock, regex_mock, diff_mock = self._make_mocks()

        diff_result = MagicMock()
        diff_result.changed_files = set()
        diff_mock.get_staged_changes.return_value = diff_result

        service = self._make_service(ts_mock, graph_mock, regex_mock, diff_mock)
        rules = [
            Rule(
                id="gr",
                description="GR",
                engine_type=EngineType.GRAPH,
                severity=Severity.HIGH,
            ),
        ]
        result = service.evaluate_changes(rules)
        assert result == []
