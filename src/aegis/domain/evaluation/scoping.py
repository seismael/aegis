"""
Domain Evaluation Scoping — re-exports from core for backward compatibility.
The canonical implementation lives in aegis.core.scoping.
"""

from aegis.core.scoping import LANG_EXT_MAP, ScopeFilter

__all__ = ["ScopeFilter", "LANG_EXT_MAP"]
