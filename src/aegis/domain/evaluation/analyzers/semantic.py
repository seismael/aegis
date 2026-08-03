"""
Domain Evaluation Semantic Analyzer — re-exports from core for backward compatibility.
The canonical implementation lives in aegis.core.analyzers.semantic.
"""

from aegis.core.analyzers.semantic import SemanticAnalyzer, SemanticAnalyzerInterface

__all__ = ["SemanticAnalyzer", "SemanticAnalyzerInterface"]
