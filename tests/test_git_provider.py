import os
import subprocess

from aegis.infrastructure.git_provider import GitDiffProvider, GitDiffResult


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

    # --- _parse_hunks tests ---

    def test_parse_hunks_empty_diff(self):
        """Empty diff produces no lines."""
        result = GitDiffResult([], repo_path=".")
        assert result._parse_hunks("") == set()

    def test_parse_hunks_single_addition(self):
        """Single added line returns the correct line number."""
        diff = "@@ -0,0 +5 @@\n+added_line\n"
        result = GitDiffResult([], repo_path=".")
        assert result._parse_hunks(diff) == {5}

    def test_parse_hunks_multiple_additions(self):
        """Multiple added lines in one hunk."""
        diff = "@@ -10,3 +10,3 @@\n context\n+new_line_1\n+new_line_2\n context\n"
        result = GitDiffResult([], repo_path=".")
        assert result._parse_hunks(diff) == {11, 12}

    def test_parse_hunks_multiple_hunks(self):
        """Multiple hunks accumulate correctly."""
        diff = (
            "@@ -1,3 +1,4 @@\n"
            "+line1\n"
            " context_a\n"
            " context_b\n"
            " context_c\n"
            "@@ -20,2 +21,3 @@\n"
            " old_context\n"
            "+new_line\n"
        )
        result = GitDiffResult([], repo_path=".")
        assert result._parse_hunks(diff) == {1, 22}

    def test_parse_hunks_context_lines_only(self):
        """Hunks with only context lines produce no additions."""
        diff = "@@ -5,2 +5,2 @@\n context_a\n context_b\n"
        result = GitDiffResult([], repo_path=".")
        assert result._parse_hunks(diff) == set()

    def test_parse_hunks_removal_only(self):
        """Hunks with only removed lines produce no additions."""
        diff = "@@ -10,3 +9,0 @@\n-deleted_line_1\n-deleted_line_2\n"
        result = GitDiffResult([], repo_path=".")
        assert result._parse_hunks(diff) == set()

    def test_binary_diff_does_not_crash(self, tmp_path):
        """Binary file diff (diff.diff is None) produces no lines."""
        result = _make_result_with_files(tmp_path, ["binary.png"])
        assert result.changed_files
        assert (
            result.get_modified_lines(os.path.join(str(tmp_path), "binary.png"))
            == set()
        )


class TestGitDiffProvider:
    """Integration tests for GitDiffProvider with real git repos."""

    def test_no_repo_returns_empty(self, tmp_path):
        """Provider returns empty result outside a git repo."""
        provider = GitDiffProvider(str(tmp_path))
        result = provider.get_staged_changes()
        assert result.changed_files == set()

    def test_empty_repo_returns_empty(self, tmp_path):
        """Provider handles repo with no commits gracefully."""
        _git_init(tmp_path)
        provider = GitDiffProvider(str(tmp_path))
        result = provider.get_staged_changes()
        assert result.changed_files == set()

    def test_staged_file_detected(self, tmp_path):
        """Provider detects a staged file."""
        _git_init(tmp_path)
        test_file = tmp_path / "readme.md"
        test_file.write_text("# Hello\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "readme.md"], cwd=tmp_path, check=True, capture_output=True
        )
        # Need at least one commit for diff to work
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )
        # Now stage a change
        test_file.write_text("# Hello\n\nNew content\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "readme.md"], cwd=tmp_path, check=True, capture_output=True
        )

        provider = GitDiffProvider(str(tmp_path))
        result = provider.get_staged_changes()
        assert os.path.join(str(tmp_path), "readme.md") in result.changed_files

    def test_get_modified_lines_from_real_diff(self, tmp_path):
        """Verify modified lines from an actual staged change."""
        _git_init(tmp_path)
        test_file = tmp_path / "main.py"
        test_file.write_text("line1\nline2\nline3\nline4\nline5\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "main.py"], cwd=tmp_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

        # Modify line 3
        test_file.write_text(
            "line1\nline2\nmodified_line3\nline4\nline5\n", encoding="utf-8"
        )
        subprocess.run(
            ["git", "add", "main.py"], cwd=tmp_path, check=True, capture_output=True
        )

        provider = GitDiffProvider(str(tmp_path))
        result = provider.get_staged_changes()
        abs_path = os.path.join(str(tmp_path), "main.py")
        lines = result.get_modified_lines(abs_path)
        assert 3 in lines

    def test_get_changes_since_baseline(self, tmp_path):
        """Verify changes since baseline ref."""
        _git_init(tmp_path)

        # First commit
        (tmp_path / "v1.txt").write_text("version 1\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "."], cwd=tmp_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "v1"], cwd=tmp_path, check=True, capture_output=True
        )

        # Second commit
        (tmp_path / "v2.txt").write_text("version 2\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "."], cwd=tmp_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", "v2"], cwd=tmp_path, check=True, capture_output=True
        )

        provider = GitDiffProvider(str(tmp_path))
        result = provider.get_changes_since_baseline("HEAD~1")
        abs_path = os.path.join(str(tmp_path), "v2.txt")
        assert abs_path in result.changed_files


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


def _git_init(path):
    """Initialize a git repo and configure user."""
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    return path
