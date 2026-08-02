"""
Domain Evaluation AST Analyzer — re-exports from core for backward compatibility.
The canonical implementation lives in aegis.core.parser.
"""

from aegis.core.parser import TreeSitterAnalyzer

__all__ = ["TreeSitterAnalyzer"]
