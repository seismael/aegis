import os
from unittest.mock import MagicMock

from aegis.core.constants import IGNORE_DIRS
from aegis.core.models.governance import EngineType, Rule, Severity
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

    def test_normalize_violation_paths(self, tmp_path):
        """Absolute violation paths are normalized to relative."""
        p = tmp_path / "src"
        p.mkdir()
        f = p / "main.py"
        f.write_text("x = 1", encoding="utf-8")

        analyzer = MagicMock(spec=RuleAnalyzerInterface)
        # Return violation with absolute path
        abs_path = str(f)
        analyzer.analyze_file.return_value = [
            ArchitecturalViolation(
                file=abs_path, line=1, rule_id="r1", description="test"
            )
        ]

        graph_mock = MagicMock(spec=GraphAnalyzerInterface)
        regex_mock = MagicMock(spec=RegexAnalyzerInterface)
        diff_provider = MagicMock(spec=DiffProviderInterface)

        service = EvaluationService(analyzer, graph_mock, regex_mock, diff_provider)
        rules = [Rule(id="r1", description="test")]
        violations = service.evaluate_workspace(str(tmp_path), rules)

        assert len(violations) == 1
        # Path should now be relative
        assert not os.path.isabs(violations[0].file), (
            f"Expected relative path, got '{violations[0].file}'"
        )

    def test_normalize_violation_paths_skips_relative(self, tmp_path):
        """Already-relative violation paths are not modified."""
        p = tmp_path / "src"
        p.mkdir()
        f = p / "main.py"
        f.write_text("x = 1", encoding="utf-8")

        analyzer = MagicMock(spec=RuleAnalyzerInterface)
        analyzer.analyze_file.return_value = [
            ArchitecturalViolation(
                file="src/main.py", line=1, rule_id="r1", description="test"
            )
        ]

        graph_mock = MagicMock(spec=GraphAnalyzerInterface)
        regex_mock = MagicMock(spec=RegexAnalyzerInterface)
        diff_provider = MagicMock(spec=DiffProviderInterface)

        service = EvaluationService(analyzer, graph_mock, regex_mock, diff_provider)
        rules = [Rule(id="r1", description="test")]
        violations = service.evaluate_workspace(str(tmp_path), rules)

        assert len(violations) == 1
        assert violations[0].file == "src/main.py"

    def test_empty_workspace_returns_no_violations(self, tmp_path):
        """Empty directory evaluation returns empty violations."""
        analyzer = MagicMock(spec=RuleAnalyzerInterface)
        graph_mock = MagicMock(spec=GraphAnalyzerInterface)
        graph_mock.analyze_graph.return_value = []
        regex_mock = MagicMock(spec=RegexAnalyzerInterface)
        diff_provider = MagicMock(spec=DiffProviderInterface)

        service = EvaluationService(analyzer, graph_mock, regex_mock, diff_provider)
        rules = [Rule(id="r1", description="test")]
        violations = service.evaluate_workspace(str(tmp_path), rules)
        assert violations == []

    def test_ignored_directories_skipped(self, tmp_path):
        """Directories in IGNORE_DIRS are skipped during evaluation."""
        for d in IGNORE_DIRS:
            (tmp_path / d).mkdir()
            (tmp_path / d / "bad.py").write_text("import os\n", encoding="utf-8")

        analyzer = MagicMock(spec=RuleAnalyzerInterface)
        graph_mock = MagicMock(spec=GraphAnalyzerInterface)
        graph_mock.analyze_graph.return_value = []
        regex_mock = MagicMock(spec=RegexAnalyzerInterface)
        diff_provider = MagicMock(spec=DiffProviderInterface)

        service = EvaluationService(analyzer, graph_mock, regex_mock, diff_provider)
        rules = [Rule(id="r1", description="test")]
        service.evaluate_workspace(str(tmp_path), rules)

        # analyzer should NOT have been called for files in ignored dirs
        analyzer.analyze_file.assert_not_called()

    def test_binary_file_does_not_crash(self, tmp_path):
        """Binary/unreadable files are skipped gracefully."""
        p = tmp_path / "src"
        p.mkdir()
        f = p / "main.py"
        f.write_text("x = 1", encoding="utf-8")

        # A binary file
        binary = p / "data.bin"
        binary.write_bytes(b"\x00\x01\x02\x03")

        analyzer = MagicMock(spec=RuleAnalyzerInterface)
        analyzer.analyze_file.return_value = []

        graph_mock = MagicMock(spec=GraphAnalyzerInterface)
        graph_mock.analyze_graph.return_value = []
        regex_mock = MagicMock(spec=RegexAnalyzerInterface)
        diff_provider = MagicMock(spec=DiffProviderInterface)

        service = EvaluationService(analyzer, graph_mock, regex_mock, diff_provider)
        rules = [Rule(id="r1", description="test")]
        # Should not crash
        violations = service.evaluate_workspace(str(tmp_path), rules)
        assert violations == []

    def test_non_python_files_filtered_by_graph_analyzer(self, tmp_path):
        """Graph analyzer should handle directories with no Python files."""
        (tmp_path / "readme.md").write_text("# Project", encoding="utf-8")
        (tmp_path / "config.json").write_text('{"key": "val"}', encoding="utf-8")

        graph_analyzer = MagicMock(spec=GraphAnalyzerInterface)
        graph_analyzer.analyze_graph.return_value = []

        service = EvaluationService(
            MagicMock(spec=RuleAnalyzerInterface),
            graph_analyzer,
            MagicMock(spec=RegexAnalyzerInterface),
            MagicMock(spec=DiffProviderInterface),
        )
        rules = [
            Rule(
                id="gr",
                engine_type=EngineType.GRAPH,
                query="disallowed_import",
                description="test",
            )
        ]
        violations = service.evaluate_workspace(str(tmp_path), rules)
        assert violations == []
        graph_analyzer.analyze_graph.assert_called_once()

    def test_evaluate_changes_handles_missing_file(self, tmp_path):
        """evaluate_changes skips files in diff that no longer exist on disk."""
        diff_result = MagicMock(spec=DiffResult)
        diff_result.changed_files = {str(tmp_path / "deleted.py")}

        diff_provider = MagicMock(spec=DiffProviderInterface)
        diff_provider.get_staged_changes.return_value = diff_result

        service = EvaluationService(
            MagicMock(spec=RuleAnalyzerInterface),
            MagicMock(spec=GraphAnalyzerInterface),
            MagicMock(spec=RegexAnalyzerInterface),
            diff_provider,
        )
        violations = service.evaluate_changes([])
        assert violations == []

    def test_derive_root_dir_from_empty_set(self):
        """_derive_root_dir with empty set returns cwd."""
        from aegis.domain.evaluation.service import EvaluationService

        root = EvaluationService._derive_root_dir(set())
        assert root == os.getcwd()

    def test_derive_root_dir_from_single_file(self, tmp_path):
        """_derive_root_dir with one file returns its parent."""
        from aegis.domain.evaluation.service import EvaluationService

        p = tmp_path / "src" / "main.py"
        root = EvaluationService._derive_root_dir({str(p)})
        assert root == str(tmp_path / "src")
