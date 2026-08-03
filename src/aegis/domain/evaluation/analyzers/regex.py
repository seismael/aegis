"""
Domain Evaluation Regex Analyzer — re-exports from core for backward compatibility.
The canonical implementation lives in aegis.core.analyzers.regex.
"""

from aegis.core.analyzers.regex import RegexAnalyzer, RegexAnalyzerInterface

__all__ = ["RegexAnalyzer", "RegexAnalyzerInterface"]
