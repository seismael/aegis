from datetime import datetime

from pydantic import BaseModel, Field


class EvolutionDecision(BaseModel):
    """
    Represents a decision made during the architectural evolution loop.
    """

    rule_id: str
    action: str  # e.g., "suppress", "relax_rule", "refactor_required"
    rationale: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)


class EvolutionLog(BaseModel):
    """
    A persistent record of architectural consensus decisions.
    """

    decisions: list[EvolutionDecision] = Field(default_factory=list)
