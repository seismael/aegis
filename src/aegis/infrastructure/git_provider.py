import os
import re

import git

from aegis.domain.evaluation.ports import DiffProviderInterface, DiffResult


class GitDiffResult(DiffResult):
    """Parsed result of staged git changes including modified line numbers."""

    def __init__(self, diff_index: git.DiffIndex, repo_path: str = "."):
        self._repo_path = repo_path
        self._raw_files: set[str] = set()
        self._modified_lines: dict[str, set[int]] = {}

        for diff in diff_index:
            path = diff.b_path or diff.a_path
            if not path:
                continue

            self._raw_files.add(path)

            if diff.diff:
                modified = self._parse_hunks(
                    diff.diff.decode("utf-8", errors="replace")
                )
                abs_path = os.path.join(self._repo_path, path)
                self._modified_lines[abs_path] = modified

    @property
    def changed_files(self) -> set[str]:
        return {os.path.join(self._repo_path, p) for p in self._raw_files}

    def get_modified_lines(self, file_path: str) -> set[int]:
        return self._modified_lines.get(file_path, set())

    def _parse_hunks(self, diff_text: str) -> set[int]:
        """
        Extracts added/modified line numbers from a unified diff text.
        """
        lines = set()
        current_line = 0

        for line in diff_text.splitlines():
            if line.startswith("@@"):
                match = re.search(r"\+(?P<start>\d+)", line)
                if match:
                    current_line = int(match.group("start"))
            elif line.startswith("+") and not line.startswith("+++"):
                lines.add(current_line)
                current_line += 1
            elif line.startswith(" "):
                current_line += 1

        return lines


class GitDiffProvider(DiffProviderInterface):
    """
    Implementation of DiffProvider using GitPython.
    """

    def __init__(self, repo_path: str = "."):
        try:
            self.repo = git.Repo(repo_path, search_parent_directories=True)
        except git.InvalidGitRepositoryError:
            self.repo = None

    def get_staged_changes(self) -> DiffResult:
        if not self.repo:
            return GitDiffResult([], repo_path=".")
        diff_index = self.repo.index.diff("HEAD")
        return GitDiffResult(diff_index, repo_path=self.repo.working_dir or ".")

    def get_changes_since_baseline(self, baseline_ref: str) -> DiffResult:
        if not self.repo:
            return GitDiffResult([], repo_path=".")
        diff_index = self.repo.head.commit.diff(baseline_ref)
        return GitDiffResult(diff_index, repo_path=self.repo.working_dir or ".")
