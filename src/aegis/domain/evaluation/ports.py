from abc import ABC, abstractmethod

from pydantic import BaseModel

from aegis.core.models.governance import Rule


class ArchitecturalViolation(BaseModel):
    """
    Represents a single architectural violation found in the codebase.
    """

    file: str
    line: int
    rule_id: str
    description: str
    severity: str = "HIGH"
    signature: str | None = None  # Hashed structural representation


class RuleAnalyzerInterface(ABC):
    """
    Interface for the polyglot code analysis engine.
    """

    @abstractmethod
    def analyze_file(
        self, file_path: str, content: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        """Analyzes a single file against a set of structural rules."""
        pass


class GraphAnalyzerInterface(ABC):
    """
    Interface for cross-file dependency graph analysis.
    """

    @abstractmethod
    def analyze_graph(
        self, root_dir: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        """Analyzes cross-file dependency relationships across the workspace."""
        pass


class RegexAnalyzerInterface(ABC):
    """
    Interface for regex-based pattern analysis within files.
    """

    @abstractmethod
    def analyze_file(
        self, file_path: str, content: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        """Analyzes file content using regex patterns defined in rules."""
        pass


class DiffResult(ABC):
    """
    Represents the set of changes in a codebase.
    """

    @property
    @abstractmethod
    def changed_files(self) -> set[str]:
        pass

    @abstractmethod
    def get_modified_lines(self, file_path: str) -> set[int]:
        """Returns the set of line numbers that were added or modified."""
        pass


class DiffProviderInterface(ABC):
    """
    Interface for providing diff information from source control.
    """

    @abstractmethod
    def get_staged_changes(self) -> DiffResult:
        """Returns changes currently in the git staging area."""
        pass

    @abstractmethod
    def get_changes_since_baseline(self, baseline_ref: str) -> DiffResult:
        """Returns changes between a baseline reference and current state."""
        pass
