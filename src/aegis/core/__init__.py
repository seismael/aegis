"""
Aegis Core Module: Policy Parser, Rule Models, AST Parsers, Baseline Manager, Scope Filter.
Pure domain engine without agent framework dependencies.
All implementations are self-contained in core/ — no imports from domain/ at module level.
"""

from aegis.core.analyzers import (
    GraphAnalyzer,
    RegexAnalyzer,
    SemanticAnalyzer,
    TreeSitterAnalyzer,
)
from aegis.core.baseline import BaselineManager, BaselineViolation
from aegis.core.evaluation import EvaluationService
from aegis.core.registry import (
    ArchitecturalViolation,
    CategoryPhaseMapping,
    EnforcementMode,
    EngineType,
    EvaluationPhase,
    RegistryLoader,
    Rule,
    RuleCategory,
    Severity,
)
from aegis.core.scoping import LANG_EXT_MAP, ScopeFilter

__all__ = [
    "Rule",
    "RuleCategory",
    "Severity",
    "EnforcementMode",
    "EvaluationPhase",
    "EngineType",
    "CategoryPhaseMapping",
    "ArchitecturalViolation",
    "RegistryLoader",
    "TreeSitterAnalyzer",
    "GraphAnalyzer",
    "RegexAnalyzer",
    "SemanticAnalyzer",
    "EvaluationService",
    "BaselineManager",
    "BaselineViolation",
    "ScopeFilter",
    "LANG_EXT_MAP",
]

