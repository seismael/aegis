"""
Aegis Core Policy Registry & Loader.
Defines immutable Pydantic rule schemas, architectural violation model,
and policy file loading logic. Zero agent-framework dependencies.
"""

import os
from enum import StrEnum
from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import BaseModel, Field

logger = structlog.get_logger()

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


# --- Core Policy Parser & Registry Loader ---


class CorePolicyParser:
    """
    Self-contained parser for declarative YAML governance rules.
    Operates strictly within core layer without dependencies on higher-level domain services.
    """

    def __init__(self, workspace_root: str | None = None):
        self.workspace_root = workspace_root or "."

    def parse_rules(self, rules_path: str) -> list[Rule]:
        """Loads rules from a YAML file."""
        path = Path(rules_path)
        if not path.exists():
            return []

        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except Exception as e:
            logger.warning("Failed to parse rule YAML file", path=rules_path, error=str(e))
            return []

        if not data or "rules" not in data:
            return []

        rules: list[Rule] = []
        for r_dict in data["rules"]:
            try:
                rules.append(Rule(**r_dict))
            except Exception as e:
                logger.warning("Skipping invalid rule in file", path=rules_path, rule_id=r_dict.get("id"), error=str(e))
        return rules

    def parse_directory(self, rules_dir: str) -> list[Rule]:
        """Scans directory recursively for YAML rule files."""
        target = Path(rules_dir)
        if not target.is_dir():
            return []

        all_rules: list[Rule] = []
        for yf in sorted(target.rglob("*.*y*ml")):
            if yf.name == "pack.yaml":
                continue
            try:
                with open(yf, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if not data or "rules" not in data:
                        continue
                    for r_dict in data["rules"]:
                        if "category" not in r_dict:
                            if yf.parent != target:
                                r_dict["category"] = yf.parent.name
                            else:
                                r_dict["category"] = yf.stem
                        try:
                            all_rules.append(Rule(**r_dict))
                        except Exception as e:
                            logger.warning("Skipping invalid rule", file=yf.name, error=str(e))
            except Exception as e:
                logger.error("Failed to parse rule file", file=yf.name, error=str(e))
        return all_rules

    def parse_all(self, workspace_root: str | None = None) -> list[Rule]:
        """Load all rules from .aegis/rules/ directory and .aegis/rules.yaml."""
        root = workspace_root or self.workspace_root
        rules_dir = os.path.join(root, ".aegis", "rules")
        rules_file = os.path.join(root, ".aegis", "rules.yaml")

        rules: list[Rule] = []
        if os.path.isdir(rules_dir):
            rules.extend(self.parse_directory(rules_dir))
        if os.path.isfile(rules_file):
            rules.extend(self.parse_rules(rules_file))

        # Deduplicate rules by rule.id
        rule_map: dict[str, Rule] = {}
        for r in rules:
            rule_map[r.id] = r
        return list(rule_map.values())


class RegistryLoader:
    """
    Loads and compiles declarative YAML governance rules into standard Pydantic Rule schemas.
    Zero domain layer imports.
    """

    @staticmethod
    def load(workspace_root: str = ".") -> list[Rule]:
        """Load all active rules from .aegis/rules in the target workspace."""
        parser = CorePolicyParser(workspace_root)
        return parser.parse_all()

    @staticmethod
    def load_from_file(file_path: str) -> list[Rule]:
        """Load rules from a specific YAML file."""
        path = Path(file_path)
        workspace = (
            str(path.parent) if path.parent.name == "rules" else str(path.parent)
        )
        parser = CorePolicyParser(workspace)
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
    "CorePolicyParser",
    "RegistryLoader",
]

