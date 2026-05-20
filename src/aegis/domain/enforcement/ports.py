from abc import ABC, abstractmethod

from pydantic import BaseModel

from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.policy.models import Rule


class FixProposal(BaseModel):
    """
    A machine-readable fix for an architectural violation.
    Can be a unified diff or a set of replacement instructions.
    """

    file: str
    diff: str | None = None
    replacement_code: str | None = None
    line_start: int | None = None
    line_end: int | None = None


class RemediationResult(BaseModel):
    """
    Structured remediation output containing both human-readable instructions
    and machine-readable fix proposals.
    """

    summary: str
    violations_count: int
    proposals: list[FixProposal] = []
    handoff_prompt: str  # The full markdown prompt for the agent


class RemediationProviderInterface(ABC):
    """
    Interface for a prompt-based remediation provider.
    Converts violations into structured prompts for AI agents.
    """

    @abstractmethod
    def generate_remediation(
        self, violations: list[ArchitecturalViolation], rules_map: dict[str, Rule]
    ) -> RemediationResult:
        """Generates structured remediation data for the given violations."""
        pass
