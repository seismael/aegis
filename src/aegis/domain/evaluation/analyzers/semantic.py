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
        violations: list[ArchitecturalViolation] = []

        semantic_rules = [r for r in rules if r.engine_type == "semantic"]
        if not semantic_rules:
            return []

        for rule in semantic_rules:
            self.logger.debug(
                "Simulating semantic evaluation", rule_id=rule.id, file=file_path
            )

            # PROOF OF CONCEPT: Simple keyword heuristic to simulate 'LLM Logic'
            # In production, this would be:
            # is_compliant = self.llm_judge(content, rule.query)

            trigger_keywords = (rule.metadata or {}).get("sim_triggers", [])
            found_triggers = [
                k for k in trigger_keywords if k.lower() in content.lower()
            ]

            if found_triggers:
                violations.append(
                    ArchitecturalViolation(
                        file=file_path,
                        line=1,  # Semantic violations are often file-level
                        rule_id=rule.id,
                        description=(
                            f"SEMANTIC VIOLATION: {rule.description} "
                            f"(Detected potential issues: {', '.join(found_triggers)})"
                        ),
                        severity=rule.severity.value,
                    )
                )

        return violations

    def build_rubric(self, target_file: str, rules: list) -> str:
        """
        Builds a re-entrant grading rubric for the parent LLM.
        The LLM reads this rubric, grades its own code, and applies fixes natively.
        """
        if not rules:
            return "NO_SEMANTIC_RULES for this file."

        rubric = f"## Semantic Grading Rubric for `{target_file}`\n\n"
        rubric += "Please evaluate the following rules using your semantic reasoning.\n"
        rubric += "For each violation found, output the fix inline.\n\n"

        for i, rule in enumerate(rules, 1):
            rubric += f"### {i}. **{rule.id}**\n"
            rubric += f"**Rule:** {rule.description}\n"
            if hasattr(rule, "rationale") and rule.rationale:
                rubric += f"**Rationale:** {rule.rationale}\n"
            rubric += f"**Severity:** {rule.severity.value}\n"
            if hasattr(rule, "query") and rule.query:
                rubric += f"**Check pattern:** `{rule.query}`\n"
            rubric += "\n"

        rubric += "---\n"
        rubric += "**Instructions:**\n"
        rubric += "1. Read the file content.\n"
        rubric += "2. For each rule above, determine if the code violates it.\n"
        rubric += "3. If a violation is found, output:\n"
        rubric += (
            "   `VIOLATION: <rule_id> - <line> - <description> - FIX: <remediation>`\n"
        )
        rubric += "4. Apply all fixes to the file.\n"
        rubric += "5. Re-run `validate_architecture_compliance` to confirm.\n"

        return rubric
