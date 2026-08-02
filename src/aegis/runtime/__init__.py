"""
Aegis Native Agent Runtime Package.

Provides in-process AST delta compilation nodes, proactive plan verifiers,
sealed tool execution wrappers, and AegisAgent state graph factories.
"""

from aegis.runtime.executor import NativeAegisExecutor
from aegis.runtime.nodes import AegisEnforcementNode, AegisFinalGate, AegisPlanVerifier
from aegis.runtime.wrappers import aegis_hardened_tool

__all__ = [
    "AegisEnforcementNode",
    "AegisFinalGate",
    "AegisPlanVerifier",
    "NativeAegisExecutor",
    "aegis_hardened_tool",
]
