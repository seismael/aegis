from typing import List, Optional
from pydantic import BaseModel
from aegis.domain.evaluation.ports import ASTViolation

class RemediationAction(BaseModel):
    """
    Represents a specific refactoring action to fix a violation.
    """
    violation: ASTViolation
    strategy: str  # e.g., "ast_transform", "llm_refactor", "regex_patch"
    description: str

class RemediationPlan(BaseModel):
    """
    A collection of actions to move the codebase toward compliance.
    """
    actions: List[RemediationAction]
    total_violations: int
    is_fully_automated: bool = False
