"""
Aegis Core Module: Policy Parser, Rule Models, AST Parsers, Baseline Manager, Scope Filter.
Pure domain engine without agent framework dependencies.
"""

from aegis.core.registry import RegistryLoader
from aegis.domain.evaluation.analyzers.ast import TreeSitterAnalyzer
from aegis.domain.evaluation.analyzers.graph import GraphAnalyzer
from aegis.domain.evaluation.analyzers.regex import RegexAnalyzer
from aegis.domain.evaluation.analyzers.semantic import SemanticAnalyzer
from aegis.domain.evaluation.baseline import BaselineManager
from aegis.domain.evaluation.scoping import ScopeFilter
from aegis.domain.policy.models import Rule, RuleCategory, Severity
from aegis.domain.policy.parser import PolicyParser

__all__ = [
    "Rule",
    "RuleCategory",
    "Severity",
    "PolicyParser",
    "RegistryLoader",
    "TreeSitterAnalyzer",
    "GraphAnalyzer",
    "RegexAnalyzer",
    "SemanticAnalyzer",
    "BaselineManager",
    "ScopeFilter",
]
