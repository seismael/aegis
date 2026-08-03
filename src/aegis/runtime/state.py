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
    Extends standard AgentState with native circuit-breaker retry state and governance audit trail.
    """

    messages: list[Any]
    pending_tool_call: dict[str, Any] | None
    governance_valid: bool
    governance_retry_count: int
    max_governance_retries: int
    circuit_broken: bool
    governance: Annotated[list[GovernanceContext], operator.add]

