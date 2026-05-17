from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Architectural violation severity levels. Maps to rule configuration."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EnforcementMode(str, Enum):
    """Enforcement action when a rule is violated. Escalates from silent to block."""

    SILENT = "silent"
    REPORT = "report"
    WARN = "warn"
    BLOCK = "block"
    FIX = "fix"


class EngineType(str, Enum):
    """Analysis engine routing discriminant. Determines which analyzer processes the rule."""

    TREE_SITTER = "tree-sitter"
    GRAPH = "graph"
    REGEX = "regex"


class Rule(BaseModel):
    """
    The 'Logical Constraint' that defines an architectural invariant.
    """

    id: str
    description: str
    severity: Severity = Severity.HIGH
    mode: EnforcementMode = EnforcementMode.BLOCK

    # Evaluation engine type (default: tree-sitter for backward compat)
    engine_type: EngineType = EngineType.TREE_SITTER

    # Language-specific query
    query: str | None = None
    language: str = "py"

    # For positive rules (X must have Y): violations = candidates - check
    candidates_query: str | None = None
    check_query: str | None = None

    # Scoping
    applies_to: list[str] = Field(default_factory=lambda: ["**/*.py"])
    excludes: list[str] = Field(default_factory=list)

    # Ownership
    owner: str | None = None

    # Human rationale for why the rule exists
    rationale: str | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)
