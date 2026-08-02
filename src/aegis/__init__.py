"""
Aegis V4 — Agent-Native Architectural Governance Engine & SDK.

Canonical exports for native agent runtime integration.
"""

from aegis.agent import AegisAgent, create_aegis_agent
from aegis.core import BaselineManager, RegistryLoader, Rule, RuleCategory, Severity
from aegis.kernel.server import AegisKernel
from aegis.runtime.executor import AegisGovernanceError, NativeAegisExecutor
from aegis.runtime.nodes import AegisEnforcementNode, AegisFinalGate, AegisPlanVerifier

__version__ = "0.4.0"

__all__ = [
    "AegisAgent",
    "create_aegis_agent",
    "AegisKernel",
    "AegisPlanVerifier",
    "AegisEnforcementNode",
    "AegisFinalGate",
    "NativeAegisExecutor",
    "AegisGovernanceError",
    "Rule",
    "RuleCategory",
    "Severity",
    "RegistryLoader",
    "BaselineManager",
]
