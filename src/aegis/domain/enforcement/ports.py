from abc import ABC, abstractmethod
from typing import Dict, List
from aegis.domain.evaluation.ports import ASTViolation
from aegis.core.models.governance import Rule


class RemediationProviderInterface(ABC):
    """
    Interface for a prompt-based remediation provider.
    Converts violations into structured prompts for AI agents.
    """

    @abstractmethod
    def generate_remediation(
        self, violations: List[ASTViolation], rules_map: Dict[str, Rule]
    ) -> str:
        """Generates a structured remediation prompt for the given violations."""
        pass
