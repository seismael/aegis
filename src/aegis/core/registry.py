"""
Aegis Core Policy Registry & Loader.
Defines immutable Pydantic rule schemas, architectural violation model,
and policy file loading logic. Zero agent-framework dependencies.
"""

from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# --- Policy Taxonomy Enums ---


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
    SEMANTIC = "semantic"
    CLOUD_ISOLATION = "cloud-isolation"
    GO = "go"
    RUST = "rust"
    JAVASCRIPT_TYPESCRIPT = "javascript-typescript"


class EngineType(StrEnum):
    """Engine routing discriminant. Determines which analyzer processes a rule."""

    TREE_SITTER = "tree-sitter"
    GRAPH = "graph"
    REGEX = "regex"
    SEMANTIC = "semantic"


# --- Configuration Models ---


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
            RuleCategory.SEMANTIC: [
                EvaluationPhase.CI,
                EvaluationPhase.ON_DEMAND,
            ],
            RuleCategory.CLOUD_ISOLATION: [
                EvaluationPhase.CI,
                EvaluationPhase.ON_DEMAND,
            ],
            RuleCategory.GO: [
                EvaluationPhase.CI,
                EvaluationPhase.ON_DEMAND,
            ],
            RuleCategory.RUST: [
                EvaluationPhase.CI,
                EvaluationPhase.ON_DEMAND,
            ],
            RuleCategory.JAVASCRIPT_TYPESCRIPT: [
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

    category: RuleCategory = RuleCategory.ARCHITECTURE

    phases: list[EvaluationPhase] | None = None

    engine_type: EngineType = EngineType.TREE_SITTER

    query: str | None = None
    language: str = "python"

    candidates_query: str | None = None
    check_query: str | None = None

    applies_to: list[str] = Field(default_factory=lambda: ["**/*.py"])
    excludes: list[str] = Field(default_factory=list)

    owner: str | None = None

    rationale: str | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)


class ArchitecturalViolation(BaseModel):
    """
    Represents a single architectural violation found in the codebase.
    """

    file: str
    line: int
    rule_id: str
    description: str
    severity: str = "HIGH"
    signature: str | None = None
    proposed_patch: str | None = None


# --- Registry Loader ---
# NOTE: RegistryLoader uses deferred imports to access PolicyParser from the
# domain layer at call time. This avoids a module-level import cycle since
# core/registry.py is the canonical source for Rule models. The domain/policy/
# layer builds on core types and adds I/O (YAML, HTTP) — core itself remains
# framework-agnostic with zero agent-orchestration dependencies at module level.


class RegistryLoader:
    """
    Loads and compiles declarative YAML governance rules into standard Pydantic Rule schemas.
    """

    @staticmethod
    def load(workspace_root: str = ".") -> list[Rule]:
        """Load all active rules from .aegis/rules in the target workspace."""
        from aegis.domain.policy.parser import PolicyParser

        parser = PolicyParser(workspace_root)
        return parser.parse_all()

    @staticmethod
    def load_from_file(file_path: str) -> list[Rule]:
        """Load rules from a specific YAML file."""
        from aegis.domain.policy.parser import PolicyParser

        path = Path(file_path)
        workspace = (
            str(path.parent) if path.parent.name == "rules" else str(path.parent)
        )
        parser = PolicyParser(workspace)
        return parser.parse_rules(str(path))


__all__ = [
    "EvaluationPhase",
    "Severity",
    "EnforcementMode",
    "RuleCategory",
    "EngineType",
    "CategoryPhaseMapping",
    "Rule",
    "ArchitecturalViolation",
    "RegistryLoader",
]
