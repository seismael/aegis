"""
Structured error protocol for MCP tool responses.
All MCP tools return str. On error, return a JSON string that both humans
and AI agents can parse programmatically.

Usage:

    return error("CONTAINER_NOT_INIT", "Kernel not initialized.",
                 hint="Call initialize_project_governance first.")
    # -> {"success": false, "error_code": "CONTAINER_NOT_INIT",
    #     "message": "Kernel not initialized.",
    #     "hint": "Call initialize_project_governance first."}

    return ok("All clear.")
    # -> "All clear."

    def err_no_spec() -> str:
        return warn("No docs/SPEC.md found.")
    # -> "WARN: No docs/SPEC.md found."
"""

import json
from typing import Any


class MCPResponse:
    """Structured response helpers for MCP tool protocol."""

    @staticmethod
    def error(code: str, message: str, *, hint: str | None = None) -> str:
        """Return a structured JSON error string for MCP tool responses."""
        payload: dict[str, Any] = {
            "success": False,
            "error_code": code,
            "message": message,
        }
        if hint:
            payload["hint"] = hint
        return json.dumps(payload)

    @staticmethod
    def ok(message: str) -> str:
        """Return a plain success string."""
        return message

    @staticmethod
    def warn(message: str) -> str:
        """Return a WARN-prefixed message (backward-compatible warning format)."""
        return f"WARN: {message}"


# Module-level aliases for ergonomic imports
error = MCPResponse.error
ok = MCPResponse.ok
warn = MCPResponse.warn

# Standardized error codes
ERR_KERNEL_NOT_INIT = "KERNEL_NOT_INIT"
ERR_SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
ERR_NOT_INITIALIZED = "NOT_INITIALIZED"
ERR_RULE_NOT_FOUND = "RULE_NOT_FOUND"
ERR_INVALID_INPUT = "INVALID_INPUT"
ERR_FILE_NOT_FOUND = "FILE_NOT_FOUND"
ERR_READ_FAILED = "READ_FAILED"
ERR_WRITE_FAILED = "WRITE_FAILED"
