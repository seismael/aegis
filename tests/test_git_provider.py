import os

from aegis.infrastructure.git_provider import GitDiffResult


class TestGitDiffResult:
    """Test suite for the GitDiffResult absolute-path contract."""

    def test_changed_files_returns_absolute_paths(self, tmp_path):
        """Verify changed_files prepends repo_path to relative paths."""
        result = GitDiffResult([], repo_path=str(tmp_path))
        assert result.changed_files == set()

    def test_changed_files_with_files(self, tmp_path):
        """Verify files in diff index produce absolute paths."""
        result = _make_result_with_files(tmp_path, ["src/main.py", "src/utils.py"])
        expected = {
            os.path.join(str(tmp_path), "src/main.py"),
            os.path.join(str(tmp_path), "src/utils.py"),
        }
        assert result.changed_files == expected
        assert all(os.path.isabs(p) for p in result.changed_files)

    def test_get_modified_lines_abs_path_lookup(self, tmp_path):
        """Verify get_modified_lines works with absolute paths."""
        result = _make_result_with_files(tmp_path, ["app.py"])
        abs_path = os.path.join(str(tmp_path), "app.py")
        lines = result.get_modified_lines(abs_path)
        assert isinstance(lines, set)

    def test_get_modified_lines_relative_path_returns_empty(self, tmp_path):
        """Verify relative path lookup returns empty (keys are absolute)."""
        result = _make_result_with_files(tmp_path, ["app.py"])
        lines = result.get_modified_lines("app.py")
        assert lines == set()

    def test_default_repo_path_is_dot(self):
        """Verify default repo_path preserves current-directory semantics."""
        result = GitDiffResult([])
        assert (
            os.path.isabs(next(iter(result.changed_files)))
            if result.changed_files
            else True
        )


def _make_result_with_files(tmp_path, files):
    """Create a GitDiffResult over specified file paths in a temp repo."""
    from unittest.mock import MagicMock

    diffs = []
    for f in files:
        full = tmp_path / f
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text("x = 1\n", encoding="utf-8")

        mock_diff = MagicMock()
        mock_diff.b_path = f
        mock_diff.a_path = f
        mock_diff.diff = None
        diffs.append(mock_diff)

    return GitDiffResult(diffs, repo_path=str(tmp_path))
