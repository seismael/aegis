"""
Domain Evaluation Baseline Manager — re-exports from core for backward compatibility.
The canonical implementation lives in aegis.core.baseline.
"""

from aegis.core.baseline import BaselineManager, BaselineViolation

__all__ = ["BaselineManager", "BaselineViolation"]
