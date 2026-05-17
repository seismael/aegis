import structlog
from typing import Dict, List
from aegis.domain.evaluation.ports import ASTViolation
from aegis.core.models.governance import Rule
from aegis.domain.enforcement.ports import RemediationProviderInterface

logger = structlog.get_logger()


class RemediationPromptSynthesizer(RemediationProviderInterface):
    """
    The 'Hands-Off' Enforcement Engine.
    Converts mathematical AST violations into rigid, context-rich
    system prompts designed to be executed by native AI agents via MCP.
    """

    def generate_remediation(
        self, violations: List[ASTViolation], rules_map: Dict[str, Rule]
    ) -> str:
        if not violations:
            return "No remediation required. Architecture is compliant."

        payload = (
            "⚠️ **AEGIS ARCHITECTURAL GOVERNANCE INTERVENTION** ⚠️\n\n"
            "Your previous code generation violated the project's strict "
            "architectural invariants. You are required to immediately "
            "refactor the following files before proceeding.\n\n"
        )

        for v in violations:
            rule: Rule | None = rules_map.get(v.rule_id)
            payload += f"### Violation in `{v.file}` (Line {v.line})\n"
            payload += f"- **Rule ID:** `{v.rule_id}` [{v.severity}]\n"
            payload += f"- **Description:** {v.description}\n"
            payload += f"- **Enforcement Mode:** "
            payload += f"{rule.mode.value if rule else 'unknown'}\n"
            if rule and rule.rationale:
                payload += f"- **Architectural Rationale:** {rule.rationale}\n"
            payload += "\n"

        payload += (
            "**Execution Directive:**\n"
            "1. Read the specified lines in the affected files.\n"
            "2. Refactor the code to eliminate the violation while "
            "preserving all existing business logic.\n"
            "3. Do not modify formatting or comments outside the "
            "targeted scope.\n"
            "4. Call the `validate_architecture_compliance` MCP tool "
            "again to verify your fix."
        )

        return payload
