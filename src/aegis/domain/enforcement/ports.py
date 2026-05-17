from abc import ABC, abstractmethod
from typing import List
from aegis.core.models.remediation import RemediationAction, RemediationPlan
from aegis.domain.evaluation.ports import ASTViolation

class RemediationStrategyInterface(ABC):
    """
    Interface for a specific remediation technique (e.g. LLM, AST).
    """
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def apply_fix(self, action: RemediationAction) -> bool:
        """Applies the fix and returns success status."""
        pass
