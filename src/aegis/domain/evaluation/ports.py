from abc import ABC, abstractmethod

from pydantic import BaseModel

from aegis.domain.policy.models import Rule


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


class SemanticAnalyzerInterface(ABC):
    """
    Interface for intent-based semantic analysis.
    Uses LLMs to evaluate rules that require high-level design context.
    """

    @abstractmethod
    def analyze_semantic(
        self, file_path: str, content: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        """Evaluates semantic intent rules against file content."""
        pass


class FixProposal(BaseModel):
    file: str
    diff: str = ""
    replacement_code: str = ""
    line_start: int = 0
    line_end: int = 0


class RemediationResult(BaseModel):
    summary: str
    violations_count: int
    proposals: list[FixProposal] = []
    handoff_prompt: str = ""


class RemediationProviderInterface(ABC):
    @abstractmethod
    def generate_remediation(
        self, violations: list[ArchitecturalViolation], rules_map: dict
    ) -> RemediationResult: ...
