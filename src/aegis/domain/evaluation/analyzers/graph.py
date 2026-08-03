"""
Domain Evaluation Graph Analyzer — re-exports from core for backward compatibility.
The canonical implementation lives in aegis.core.analyzers.graph.
"""

import ast
import os

from aegis.core.analyzers.graph import (
    _MAX_FILE_BYTES,
    IGNORE_DIRS,
    GraphAnalyzer,
    GraphAnalyzerInterface,
)

__all__ = [
    "GraphAnalyzer",
    "GraphAnalyzerInterface",
    "os",
    "ast",
    "_MAX_FILE_BYTES",
    "IGNORE_DIRS",
]
