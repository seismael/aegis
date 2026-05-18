from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EvaluationPhase(StrEnum):
    """Temporal phase determining when a rule is evaluated."""

    PRE_COMMIT = "pre-commit"
    PRE_PUSH = "pre-push"
    CI = "ci"
    NIGHTLY = "nightly"
    ON_DEMAND = "on-demand"


class Severity(StrEnum):
    """Architectural violation severity levels. Maps to rule configuration."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    WARN = "WARN"


class EnforcementMode(StrEnum):
    """Enforcement action when a rule is violated. Escalates from silent to block."""

    SILENT = "silent"
    REPORT = "report"
    WARN = "warn"
    BLOCK = "block"
    FIX = "fix"


class RuleCategory(StrEnum):
    """
    Policy taxonomy. Determines enforcement priority,
    baseline eligibility, and phase defaults.
    """

    ARCHITECTURE = "architecture"
    SECURITY = "security"
    TESTING = "testing"
    STYLE = "style"
    STRUCTURE = "structure"
    DESIGN = "design"
    BEST_PRACTICES = "best-practices"
    TOOLS = "tools"
    PERFORMANCE = "performance"
    DOCUMENTATION = "documentation"
    DEPENDENCIES = "dependencies"
    INFRASTRUCTURE = "infrastructure"
    GENERAL = "general"


class EngineType(StrEnum):
    """Engine routing discriminant. Determines which analyzer processes a rule."""

    TREE_SITTER = "tree-sitter"
    GRAPH = "graph"
    REGEX = "regex"


class CategoryPhaseMapping(BaseModel):
    """Default evaluation phases per rule category.

    Rules without explicit ``phases`` inherit defaults from this mapping.
    """

    category_defaults: dict[RuleCategory, list[EvaluationPhase]] = Field(
        default_factory=lambda: {
            RuleCategory.STYLE: [EvaluationPhase.PRE_COMMIT],
            RuleCategory.BEST_PRACTICES: [
                EvaluationPhase.PRE_COMMIT,
                EvaluationPhase.CI,
            ],
            RuleCategory.DOCUMENTATION: [
                EvaluationPhase.PRE_COMMIT,
                EvaluationPhase.CI,
            ],
            RuleCategory.ARCHITECTURE: [
                EvaluationPhase.PRE_PUSH,
                EvaluationPhase.CI,
            ],
            RuleCategory.STRUCTURE: [
                EvaluationPhase.PRE_PUSH,
                EvaluationPhase.CI,
            ],
            RuleCategory.TESTING: [
                EvaluationPhase.PRE_COMMIT,
                EvaluationPhase.CI,
            ],
            RuleCategory.SECURITY: [
                EvaluationPhase.CI,
                EvaluationPhase.NIGHTLY,
                EvaluationPhase.ON_DEMAND,
            ],
            RuleCategory.DESIGN: [
                EvaluationPhase.CI,
                EvaluationPhase.ON_DEMAND,
            ],
            RuleCategory.PERFORMANCE: [
                EvaluationPhase.CI,
                EvaluationPhase.NIGHTLY,
            ],
            RuleCategory.DEPENDENCIES: [
                EvaluationPhase.NIGHTLY,
                EvaluationPhase.CI,
            ],
            RuleCategory.INFRASTRUCTURE: [
                EvaluationPhase.CI,
                EvaluationPhase.ON_DEMAND,
            ],
            RuleCategory.TOOLS: [
                EvaluationPhase.CI,
                EvaluationPhase.ON_DEMAND,
            ],
            RuleCategory.GENERAL: [EvaluationPhase.ON_DEMAND],
        }
    )


class Rule(BaseModel):
    """
    The 'Logical Constraint' that defines an architectural invariant.
    """

    id: str
    description: str
    severity: Severity = Severity.HIGH
    mode: EnforcementMode = EnforcementMode.BLOCK

    # Policy taxonomy (backward-compat default: architecture)
    category: RuleCategory = RuleCategory.ARCHITECTURE

    # Evaluation phase(s) — None means resolve from CategoryPhaseMapping
    phases: list[EvaluationPhase] | None = None

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
