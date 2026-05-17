import git

from aegis.domain.evaluation.ports import DiffProviderInterface, DiffResult


class GitDiffResult(DiffResult):
    """Parsed result of staged git changes including modified line numbers."""

    def __init__(self, diff_index: git.DiffIndex):
        self._changed_files: set[str] = set()
        self._modified_lines: dict[str, set[int]] = {}

        for diff in diff_index:
            path = diff.b_path or diff.a_path
            if path:
                self._changed_files.add(path)

            # Parse diff hunks to get exact modified lines
            if diff.diff:
                modified = self._parse_hunks(
                    diff.diff.decode("utf-8", errors="replace")
                )
                self._modified_lines[path] = modified

    def _parse_hunks(self, diff_text: str) -> set[int]:
        """
        Extracts added/modified line numbers from a unified diff text.
        """
        lines = set()
        current_line = 0

        for line in diff_text.splitlines():
            if line.startswith("@@"):
                # Format: @@ -start,len +start,len @@
                match = re.search(r"\+(?P<start>\d+)", line)
                if match:
                    current_line = int(match.group("start"))
            elif line.startswith("+") and not line.startswith("+++"):
                lines.add(current_line)
                current_line += 1
            elif line.startswith(" "):
                current_line += 1
            elif line.startswith("-") and not line.startswith("---"):
                # Line removed, doesn't affect our 'modified' set for current file state
                pass

        return lines

    @property
    def changed_files(self) -> set[str]:
        return self._changed_files

    def get_modified_lines(self, file_path: str) -> set[int]:
        return self._modified_lines.get(file_path, set())


import re


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
            return GitDiffResult([])
        diff_index = self.repo.index.diff("HEAD")
        return GitDiffResult(diff_index)

    def get_changes_since_baseline(self, baseline_ref: str) -> DiffResult:
        if not self.repo:
            return GitDiffResult([])
        diff_index = self.repo.head.commit.diff(baseline_ref)
        return GitDiffResult(diff_index)
