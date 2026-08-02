"""
Native Hardened Tool Executor Wrapper for Aegis.

Intercepts tool execution payloads in-memory, performing AST delta evaluation
and rule enforcement before committing file system modifications.
"""

from collections.abc import Callable
from typing import Any

from aegis.domain.evaluation.service import EvaluationService
from aegis.domain.policy.models import Rule


class AegisGovernanceError(Exception):
    """Raised when a tool call violates Aegis architectural invariants."""

    def __init__(self, message: str, violations: list[dict]):
        super().__init__(message)
        self.violations = violations


class NativeAegisExecutor:
    """
    Hardened Tool Executor.
    Wraps tool executions to enforce Aegis rules in-process before I/O execution.
    """

    def __init__(self, evaluation_service: EvaluationService, rules: list[Rule]):
        self.evaluation = evaluation_service
        self.rules = rules

    def execute_tool(
        self, tool_name: str, tool_args: dict[str, Any], tool_fn: Callable[..., Any]
    ) -> Any:
        """
        Interceptors write/edit tool calls (e.g. write_file, replace_content)
        and evaluates code payload against rules before delegating to tool_fn.
        """
        # Intercept code-modifying tools
        content_keys = ("content", "code", "replacement", "code_content")
        code_payload = None
        for key in content_keys:
            if key in tool_args and isinstance(tool_args[key], str):
                code_payload = tool_args[key]
                break

        if code_payload:
            language = tool_args.get("language", "python")
            violations = self.evaluation.evaluate_code_string(
                code_payload, language, self.rules
            )

            # Blocking severity threshold check
            blocking = [
                v for v in violations if v.severity in ("CRITICAL", "HIGH", "BLOCK")
            ]
            if blocking:
                violation_dicts = [v.model_dump() for v in blocking]
                raise AegisGovernanceError(
                    f"Aegis Governance Enforcement: Tool '{tool_name}' blocked due to "
                    f"{len(blocking)} architectural violation(s).",
                    violations=violation_dicts,
                )

        return tool_fn(**tool_args)
