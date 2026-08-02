"""
Tool Hardening Decorators for Aegis Native Execution.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from aegis.domain.evaluation.service import EvaluationService
from aegis.domain.policy.models import Rule
from aegis.runtime.executor import NativeAegisExecutor


def aegis_hardened_tool(
    evaluation_service: EvaluationService, rules: list[Rule]
) -> Callable:
    """
    Decorator to seal a tool function against architectural violations.

    Usage:
        @aegis_hardened_tool(evaluation_service, rules)
        def write_code(path: str, content: str):
            ...
    """

    executor = NativeAegisExecutor(evaluation_service, rules)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Bind args to kwargs for executor inspection
            return executor.execute_tool(
                tool_name=func.__name__,
                tool_args=kwargs,
                tool_fn=lambda **kw: func(*args, **kw),
            )

        return wrapper

    return decorator
