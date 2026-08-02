"""
Domain Evaluation Service — re-exports from canonical location for backward compatibility.
The canonical implementation lives in aegis.domain.evaluation_service.
"""

from aegis.domain.evaluation_service import EvaluationService

__all__ = ["EvaluationService"]
