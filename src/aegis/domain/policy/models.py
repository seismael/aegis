"""
Domain Policy Models — re-exports from core for backward compatibility.
The canonical definitions live in aegis.core.registry.
"""

from aegis.core.registry import (
    ArchitecturalViolation,
    CategoryPhaseMapping,
    EnforcementMode,
    EngineType,
    EvaluationPhase,
    Rule,
    RuleCategory,
    Severity,
)

__all__ = [
    "EvaluationPhase",
    "Severity",
    "EnforcementMode",
    "RuleCategory",
    "EngineType",
    "CategoryPhaseMapping",
    "Rule",
    "ArchitecturalViolation",
]
