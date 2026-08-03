"""
Aegis Core Semantic Engine.
Evaluates natural language intent rubrics for agent-native self-assessment.
Zero agent-framework dependencies.
"""

from abc import ABC, abstractmethod

import structlog

from aegis.core.registry import ArchitecturalViolation, Rule

logger = structlog.get_logger()


class SemanticAnalyzerInterface(ABC):
    """Interface for intent-based semantic analysis."""

    @abstractmethod
    def analyze_semantic(
        self, file_path: str, content: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        pass


class SemanticAnalyzer(SemanticAnalyzerInterface):
    """
    Semantic Analyzer for Intent-Based Governance.
    Generates rubrics for parent agent self-evaluation and provides heuristic keyword scanning for CI.
    """

    def __init__(self):
        self.logger = structlog.get_logger()

    def analyze_semantic(
        self, file_path: str, content: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        violations: list[ArchitecturalViolation] = []

        semantic_rules = [r for r in rules if r.engine_type == "semantic"]
        if not semantic_rules:
            return []

        for rule in semantic_rules:
            self.logger.debug("Semantic rule detected", rule_id=rule.id, file=file_path)

            trigger_keywords = (rule.metadata or {}).get("sim_triggers", [])
            found_triggers = [
                k for k in trigger_keywords if k.lower() in content.lower()
            ]

            if found_triggers:
                violations.append(
                    ArchitecturalViolation(
                        file=file_path,
                        line=1,
                        rule_id=rule.id,
                        description=(
                            f"POTENTIAL SEMANTIC VIOLATION: {rule.description} "
                            f"(Detected triggers: {', '.join(found_triggers)})"
                        ),
                        severity=rule.severity.value,
                    )
                )

        return violations

    def build_rubric(self, target_file: str, rules: list[Rule]) -> str:
        """Builds a re-entrant grading rubric for the parent LLM."""
        if not rules:
            return f"NO_SEMANTIC_RULES for `{target_file}`."

        rubric = f"### 🧩 Semantic Grading Rubric for `{target_file}`\n\n"
        rubric += "This file is subject to high-level architectural intents that require your semantic reasoning to validate.\n\n"
        rubric += "| Rule ID | Intent / Description | Severity |\n"
        rubric += "| :--- | :--- | :--- |\n"

        for rule in rules:
            rubric += (
                f"| **{rule.id}** | {rule.description} | `{rule.severity.value}` |\n"
            )

        rubric += "\n#### 📋 Instructions for Agent-Native Self-Evaluation:\n\n"
        rubric += "1. **Analyze**: Review the file content against the intents listed above.\n"
        rubric += "2. **Identify**: If any code block violates these intents, report it.\n"
        rubric += "3. **Report Format**: `VIOLATION: <rule_id> - <line_number> - <reasoning> - FIX: <suggested_change>`\n"
        rubric += "4. **Remediate**: Apply necessary changes natively.\n"
        rubric += "5. **Verify**: After fixing, call `check_architecture` again.\n"

        return rubric


__all__ = ["SemanticAnalyzer", "SemanticAnalyzerInterface"]
