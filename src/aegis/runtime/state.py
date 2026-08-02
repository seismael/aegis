"""
Aegis Runtime State Schemas.
Defines GovernanceContext and AegisState schemas for native graph state injection.
"""

import operator
from typing import Annotated, Any, TypedDict


class GovernanceContext(TypedDict):
    """Governance execution context audit trail."""
    is_clean: bool
    total_violations: int
    active_violations: list[dict[str, Any]]
    remediation_prompt: str | None


class AegisState(TypedDict):
    """
    Governance-hardened AgentState schema.
    Extends standard AgentState with a native governance audit trail reducer.
    """
    messages: list[Any]
    pending_tool_call: dict[str, Any] | None
    governance_valid: bool
    governance: Annotated[list[GovernanceContext], operator.add]
