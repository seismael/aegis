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
