from abc import ABC, abstractmethod

from aegis.core.models.governance import Rule
from aegis.domain.evaluation.ports import ArchitecturalViolation


class RemediationProviderInterface(ABC):
    """
    Interface for a prompt-based remediation provider.
    Converts violations into structured prompts for AI agents.
    """

    @abstractmethod
    def generate_remediation(
        self, violations: list[ArchitecturalViolation], rules_map: dict[str, Rule]
    ) -> str:
        """Generates a structured remediation prompt for the given violations."""
        pass
