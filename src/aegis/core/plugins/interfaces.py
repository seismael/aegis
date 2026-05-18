from collections.abc import Callable

from aegis.domain.evaluation.ports import ArchitecturalViolation, RuleAnalyzerInterface
from aegis.domain.policy.models import Rule


class CustomAnalyzerInterface(RuleAnalyzerInterface):
    """
    Advanced interface for Aegis plugins.
    Allows plugins to provide their own rules, perform project-wide analysis,
    and provide specialized remediation logic.
    """

    @property
    def mcp_tools(self) -> list[Callable]:
        """Optional list of MCP tool functions for the kernel to register."""
        return []

    def register_rules(self) -> list[Rule]:
        """
        Allows the plugin to provide built-in rules.
        These are automatically added to the evaluation loop.
        """
        return []

    def analyze_project(
        self, _root_dir: str, _rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        """
        Hook for project-wide analysis.
        Useful for rules that require a global view (e.g., dead code, global coupling).
        """
        return []

    def provide_remediation(
        self, _violation: ArchitecturalViolation, _rule: Rule
    ) -> str | None:
        """
        Allows the plugin to provide custom fix instructions for a violation.
        If it returns None, Aegis falls back to the default rule description.
        """
        return None

    def on_evaluation_start(self, root_dir: str) -> None:
        """Lifecycle hook called before analysis starts."""
        pass

    def on_evaluation_end(self, violations: list[ArchitecturalViolation]) -> None:
        """Lifecycle hook called after all analysis is complete."""
        pass
