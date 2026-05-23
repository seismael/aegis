import os
from unittest.mock import MagicMock

from aegis.domain.evaluation.constants import IGNORE_DIRS
from aegis.domain.evaluation.ports import (
    ArchitecturalViolation,
    DiffProviderInterface,
    DiffResult,
    GraphAnalyzerInterface,
    RegexAnalyzerInterface,
    RuleAnalyzerInterface,
)
from aegis.domain.evaluation.service import EvaluationService
from aegis.domain.policy.models import EngineType, Rule, Severity


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

    def test_evaluate_workspace_empty_rules_returns_early(self, tmp_path):
        """No rules after phase/category filtering → immediate empty return."""
        service = self._make_service()
        p = tmp_path / "src"
        p.mkdir()
        (p / "main.py").write_text("x = 1", encoding="utf-8")

        violations = service.evaluate_workspace(str(tmp_path), [])
        assert violations == []
        # No analyzers should have been invoked
        service.tree_sitter_analyzer.analyze_file.assert_not_called()
        service.graph_analyzer.analyze_graph.assert_not_called()
        service.regex_analyzer.analyze_file.assert_not_called()

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

    def test_evaluate_changes_filters_by_modified_lines(self, tmp_path):
        """Violation on a modified line is included."""
        f = tmp_path / "src" / "main.py"
        f.parent.mkdir(parents=True)
        f.write_text("line1\nline2\nline3\n", encoding="utf-8")

        analyzer = MagicMock(spec=RuleAnalyzerInterface)
        analyzer.analyze_file.return_value = [
            ArchitecturalViolation(file=str(f), line=2, rule_id="r1", description="bad")
        ]

        diff_result = MagicMock(spec=DiffResult)
        diff_result.changed_files = {str(f)}
        diff_result.get_modified_lines.return_value = {2}

        diff_provider = MagicMock(spec=DiffProviderInterface)
        diff_provider.get_staged_changes.return_value = diff_result

        service = EvaluationService(
            analyzer,
            MagicMock(spec=GraphAnalyzerInterface),
            MagicMock(spec=RegexAnalyzerInterface),
            diff_provider,
        )
        rules = [Rule(id="r1", description="test")]
        violations = service.evaluate_changes(rules, root_dir=str(tmp_path))
        assert len(violations) == 1

    def test_evaluate_changes_excludes_unmodified_lines(self, tmp_path):
        """Violation NOT on a modified line is excluded."""
        f = tmp_path / "src" / "main.py"
        f.parent.mkdir(parents=True)
        f.write_text("line1\nline2\nline3\n", encoding="utf-8")

        analyzer = MagicMock(spec=RuleAnalyzerInterface)
        analyzer.analyze_file.return_value = [
            ArchitecturalViolation(file=str(f), line=2, rule_id="r1", description="bad")
        ]

        diff_result = MagicMock(spec=DiffResult)
        diff_result.changed_files = {str(f)}
        diff_result.get_modified_lines.return_value = {3}

        diff_provider = MagicMock(spec=DiffProviderInterface)
        diff_provider.get_staged_changes.return_value = diff_result

        service = EvaluationService(
            analyzer,
            MagicMock(spec=GraphAnalyzerInterface),
            MagicMock(spec=RegexAnalyzerInterface),
            diff_provider,
        )
        rules = [Rule(id="r1", description="test")]
        violations = service.evaluate_changes(rules, root_dir=str(tmp_path))
        assert len(violations) == 0

    def test_evaluate_changes_skips_graph_rules(self, tmp_path):
        """Graph rules are skipped during staged evaluation."""
        f = tmp_path / "main.py"
        f.write_text("x = 1", encoding="utf-8")

        analyzer = MagicMock(spec=RuleAnalyzerInterface)
        diff_result = MagicMock(spec=DiffResult)
        diff_result.changed_files = {str(f)}
        diff_result.get_modified_lines.return_value = {1}
        diff_provider = MagicMock(spec=DiffProviderInterface)
        diff_provider.get_staged_changes.return_value = diff_result

        graph_mock = MagicMock(spec=GraphAnalyzerInterface)
        service = EvaluationService(
            analyzer,
            graph_mock,
            MagicMock(spec=RegexAnalyzerInterface),
            diff_provider,
        )
        rules = [
            Rule(
                id="g1",
                engine_type=EngineType.GRAPH,
                query="circular_dependency",
                description="cycle",
            )
        ]
        violations = service.evaluate_changes(rules, root_dir=str(tmp_path))
        assert violations == []
        graph_mock.analyze_graph.assert_not_called()

    def test_evaluate_changes_uses_both_ts_and_regex(self, tmp_path):
        """Both ts and regex analyzers are called during staged eval."""
        f = tmp_path / "main.py"
        f.write_text("print('x')\n", encoding="utf-8")

        ts_analyzer = MagicMock(spec=RuleAnalyzerInterface)
        ts_analyzer.analyze_file.return_value = []
        regex_analyzer = MagicMock(spec=RegexAnalyzerInterface)
        regex_analyzer.analyze_file.return_value = []

        diff_result = MagicMock(spec=DiffResult)
        diff_result.changed_files = {str(f)}
        diff_result.get_modified_lines.return_value = {1}
        diff_provider = MagicMock(spec=DiffProviderInterface)
        diff_provider.get_staged_changes.return_value = diff_result

        service = EvaluationService(
            ts_analyzer,
            MagicMock(spec=GraphAnalyzerInterface),
            regex_analyzer,
            diff_provider,
        )
        rules = [
            Rule(id="r1", engine_type=EngineType.TREE_SITTER, description="ast"),
            Rule(id="r2", engine_type=EngineType.REGEX, description="re"),
        ]
        service.evaluate_changes(rules, root_dir=str(tmp_path))
        ts_analyzer.analyze_file.assert_called_once()
        regex_analyzer.analyze_file.assert_called_once()

    def test_evaluate_changes_logs_on_read_error(self, tmp_path):
        """evaluate_changes does not crash when a file cannot be read."""
        diff_result = MagicMock(spec=DiffResult)
        diff_result.changed_files = {str(tmp_path / "no_perms.py")}
        diff_result.get_modified_lines.return_value = {1}
        diff_provider = MagicMock(spec=DiffProviderInterface)
        diff_provider.get_staged_changes.return_value = diff_result

        service = EvaluationService(
            MagicMock(spec=RuleAnalyzerInterface),
            MagicMock(spec=GraphAnalyzerInterface),
            MagicMock(spec=RegexAnalyzerInterface),
            diff_provider,
        )
        violations = service.evaluate_changes([], root_dir=str(tmp_path))
        assert violations == []

    def test_derive_root_dir_from_empty_set(self):
        """_derive_root_dir with empty set returns cwd."""
        root = EvaluationService._derive_root_dir(set())
        assert root == os.getcwd()

    def test_derive_root_dir_from_single_file(self, tmp_path):
        """_derive_root_dir with one file returns its parent."""
        p = tmp_path / "src" / "main.py"
        root = EvaluationService._derive_root_dir({str(p)})
        assert root == str(tmp_path / "src")

    def test_derive_root_dir_handles_value_error(self):
        """_derive_root_dir with cross-drive paths on Windows returns cwd."""
        try:
            root = EvaluationService._derive_root_dir({"C:\\a.py", "D:\\b.py"})
            assert root == os.getcwd()
        except ValueError:
            pass  # os.path.commonpath raises on some Python versions


class TestEvaluateFile:
    """Tests for EvaluationService.evaluate_file."""

    def _make_service(self, ts_analyzer=None, regex_analyzer=None):
        return EvaluationService(
            tree_sitter_analyzer=ts_analyzer or MagicMock(spec=RuleAnalyzerInterface),
            graph_analyzer=MagicMock(spec=GraphAnalyzerInterface),
            regex_analyzer=regex_analyzer or MagicMock(spec=RegexAnalyzerInterface),
            diff_provider=MagicMock(spec=DiffProviderInterface),
        )

    def test_evaluate_file_returns_violations(self, tmp_path):
        """evaluate_file returns violations from analyzers."""
        f = tmp_path / "main.py"
        f.write_text("print('hello')\n", encoding="utf-8")
        regex_analyzer = MagicMock(spec=RegexAnalyzerInterface)
        regex_analyzer.analyze_file.return_value = [
            ArchitecturalViolation(
                file=str(f),
                line=1,
                rule_id="r1",
                description="no print",
            )
        ]
        service = self._make_service(regex_analyzer=regex_analyzer)
        rules = [Rule(id="r1", engine_type=EngineType.REGEX, description="no print")]
        violations = service.evaluate_file(str(f), rules, root_dir=str(tmp_path))
        assert len(violations) == 1
        assert violations[0].rule_id == "r1"

    def test_evaluate_file_nonexistent(self, tmp_path):
        """evaluate_file returns empty list for unreadable file."""
        service = self._make_service()
        rules = [Rule(id="r1", description="test")]
        violations = service.evaluate_file(
            str(tmp_path / "nonexistent.py"), rules, root_dir=str(tmp_path)
        )
        assert violations == []

    def test_evaluate_file_scope_filter_applied(self, tmp_path):
        """evaluate_file applies ScopeFilter excludes."""
        f = tmp_path / "main.py"
        f.write_text("x = 1\n", encoding="utf-8")
        regex_analyzer = MagicMock(spec=RegexAnalyzerInterface)
        regex_analyzer.analyze_file.return_value = [
            ArchitecturalViolation(file=str(f), line=1, rule_id="r1", description="x")
        ]
        service = self._make_service(regex_analyzer=regex_analyzer)
        # Rule with excludes that covers the file
        rules = [
            Rule(
                id="r1",
                engine_type=EngineType.REGEX,
                description="x",
                excludes=["main.py"],
            )
        ]
        violations = service.evaluate_file(str(f), rules, root_dir=str(tmp_path))
        assert violations == []

    def test_evaluate_file_uses_both_ts_and_regex(self, tmp_path):
        """evaluate_file calls both ts and regex analyzers."""
        f = tmp_path / "main.py"
        f.write_text("x = 1\n", encoding="utf-8")
        ts_analyzer = MagicMock(spec=RuleAnalyzerInterface)
        ts_analyzer.analyze_file.return_value = []
        regex_analyzer = MagicMock(spec=RegexAnalyzerInterface)
        regex_analyzer.analyze_file.return_value = []
        service = EvaluationService(
            tree_sitter_analyzer=ts_analyzer,
            graph_analyzer=MagicMock(spec=GraphAnalyzerInterface),
            regex_analyzer=regex_analyzer,
            diff_provider=MagicMock(spec=DiffProviderInterface),
        )
        rules = [
            Rule(id="t1", engine_type=EngineType.TREE_SITTER, description="ts"),
            Rule(id="r1", engine_type=EngineType.REGEX, description="re"),
        ]
        service.evaluate_file(str(f), rules, root_dir=str(tmp_path))
        ts_analyzer.analyze_file.assert_called_once()
        regex_analyzer.analyze_file.assert_called_once()


class TestEvaluateCodeString:
    """Tests for EvaluationService.evaluate_code_string — in-memory evaluation."""

    def _make_service(self, ts_analyzer=None, regex_analyzer=None):
        return EvaluationService(
            tree_sitter_analyzer=ts_analyzer or MagicMock(spec=RuleAnalyzerInterface),
            graph_analyzer=MagicMock(spec=GraphAnalyzerInterface),
            regex_analyzer=regex_analyzer or MagicMock(spec=RegexAnalyzerInterface),
            diff_provider=MagicMock(spec=DiffProviderInterface),
        )

    def test_empty_code_returns_empty(self):
        """Empty code string returns empty list."""
        service = self._make_service()
        rules = [Rule(id="r1", description="test", language="py")]
        result = service.evaluate_code_string("", "py", rules)
        assert result == []

    def test_empty_rules_returns_empty(self):
        """Empty rules list returns empty list."""
        service = self._make_service()
        result = service.evaluate_code_string("def f(): pass", "py", [])
        assert result == []

    def test_no_matching_rules(self):
        """Language mismatch returns empty list."""
        service = self._make_service()
        rules = [Rule(id="r1", description="test", language="rs")]
        result = service.evaluate_code_string("def f(): pass", "py", rules)
        assert result == []

    def test_regex_violation_detected(self):
        """Regex analyzer detects violation in code string."""
        from aegis.domain.evaluation.ports import ArchitecturalViolation

        regex_analyzer = MagicMock(spec=RegexAnalyzerInterface)
        regex_analyzer.analyze_file.return_value = [
            ArchitecturalViolation(
                file="memory.py", line=1, rule_id="r1", description="no print"
            )
        ]
        service = self._make_service(regex_analyzer=regex_analyzer)
        rules = [
            Rule(
                id="r1",
                description="no print",
                engine_type=EngineType.REGEX,
                language="py",
            )
        ]
        violations = service.evaluate_code_string("print('x')", "py", rules)
        assert len(violations) == 1
        assert violations[0].rule_id == "r1"

    def test_synthetic_path_extension_resolution(self):
        """Analyzer receives synthetic path with correct extension per language."""
        ts_analyzer = MagicMock(spec=RuleAnalyzerInterface)
        ts_analyzer.analyze_file.return_value = []
        service = self._make_service(ts_analyzer=ts_analyzer)
        rules = [
            Rule(
                id="r1",
                description="test",
                engine_type=EngineType.TREE_SITTER,
                language="tsx",
            )
        ]
        service.evaluate_code_string("const x: number = 1;", "tsx", rules)
        # Verify the synthetic path passed to analyzer ends in .tsx
        call_args = ts_analyzer.analyze_file.call_args[0]
        assert call_args[0] == "memory.tsx"
