"""
Innovative Semantic Engine for Aegis.

Uses Large Language Models (LLMs) to evaluate architectural intent
that cannot be captured by syntactic (AST/Regex) rules alone.

Example Semantic Rule:
  - id: sec-no-pii-exposure
    description: "Ensure no PII (emails, SSNs) is logged or exposed in API responses."
    engine_type: semantic
    query: "Does this code log or return any personally identifiable information?"
"""

import structlog

from aegis.domain.evaluation.ports import (
    ArchitecturalViolation,
    SemanticAnalyzerInterface,
)
from aegis.domain.policy.models import Rule


class SemanticAnalyzer(SemanticAnalyzerInterface):
    """
    Simulated Semantic Analyzer (Proof of Concept).
    In a full implementation, this would call an LLM (e.g. GPT-4, Claude 3)
    to judge code compliance against natural language design intents.
    """

    def __init__(self):
        self.logger = structlog.get_logger()

    def analyze_semantic(
        self, file_path: str, content: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        """
        In an agent-native architecture, analyze_semantic identifies if
        semantic rules exist. If they do, the engine primarily signals that
        a rubric-based evaluation is required by the parent LLM.
        """
        violations: list[ArchitecturalViolation] = []

        semantic_rules = [r for r in rules if r.engine_type == "semantic"]
        if not semantic_rules:
            return []

        for rule in semantic_rules:
            self.logger.debug(
                "Semantic rule detected", rule_id=rule.id, file=file_path
            )

            # HEURISTIC: We still provide a basic heuristic for immediate feedback
            # in non-interactive CI environments, but the "re-entrant" rubric
            # is the primary source of truth for the Agent.
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
        """
        Builds a re-entrant grading rubric for the parent LLM.
        The LLM reads this rubric, grades its own code, and applies fixes natively.
        """
        if not rules:
            return f"NO_SEMANTIC_RULES for `{target_file}`."

        rubric = f"### 🧩 Semantic Grading Rubric for `{target_file}`\n\n"
        rubric += "This file is subject to high-level architectural intents that require your semantic reasoning to validate.\n\n"
        rubric += "| Rule ID | Intent / Description | Severity |\n"
        rubric += "| :--- | :--- | :--- |\n"

        for rule in rules:
            rubric += f"| **{rule.id}** | {rule.description} | `{rule.severity.value}` |\n"

        rubric += "\n#### 📋 Instructions for Agent-Native Self-Evaluation:\n\n"
        rubric += "1. **Analyze**: Review the file content against the intents listed above.\n"
        rubric += "2. **Identify**: If any code block violates these intents, you MUST report it.\n"
        rubric += "3. **Report Format**: Use the following format for each violation:\n"
        rubric += "   - `VIOLATION: <rule_id> - <line_number> - <reasoning> - FIX: <suggested_change>`\n"
        rubric += "4. **Remediate**: Apply the necessary changes to align the code with the architectural intent.\n"
        rubric += "5. **Verify**: After fixing, call `validate_architecture_compliance` again to ensure no further issues exist.\n"

        return rubric
