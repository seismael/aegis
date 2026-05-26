import os

import structlog

from aegis.domain.evaluation.ports import (
    ArchitecturalViolation,
    RemediationProviderInterface,
    RemediationResult,
)
from aegis.domain.policy.models import Rule

logger = structlog.get_logger()


class RemediationPromptSynthesizer(RemediationProviderInterface):
    """
    Converts mathematical AST violations into rigid, context-rich
    system prompts designed to be executed by native AI agents via MCP.
    Agent-Native V4: All outputs are strings for LLM consumption.
    """

    def __init__(self, extra_analyzers: list | None = None):
        self.extra_analyzers = extra_analyzers or []

    def generate_remediation(
        self, violations: list[ArchitecturalViolation], rules_map: dict[str, Rule]
    ) -> RemediationResult:
        if not violations:
            return RemediationResult(
                summary="No remediation required. Architecture is compliant.",
                violations_count=0,
                handoff_prompt="SUCCESS: Architecture compliant.",
            )

        payload = (
            "**AEGIS ARCHITECTURAL GOVERNANCE INTERVENTION**\n\n"
            "Your previous code generation violated the project's strict "
            "architectural invariants. You are required to immediately "
            "refactor the following files before proceeding.\n\n"
        )

        max_display = 25
        displayed = violations[:max_display]
        truncated = len(violations) - max_display

        for v in displayed:
            rule = rules_map.get(v.rule_id)
            is_security = rule is not None and rule.category.value == "security"

            if is_security:
                payload += (
                    f"### [CRITICAL SECURITY VULNERABILITY] in `{v.file}`"
                    f" (Line {v.line})\n"
                )
                payload += (
                    "**DIRECTIVE: Prioritize secure coding practices"
                    " over performance or brevity.**\n"
                )
            else:
                payload += f"### Violation in `{v.file}` (Line {v.line})\n"
            payload += f"- **Rule ID:** `{v.rule_id}` [{v.severity}]\n"

            custom_desc = None
            for extra in self.extra_analyzers:
                if hasattr(extra, "provide_remediation"):
                    custom_desc = extra.provide_remediation(v, rule)
                    if custom_desc:
                        break

            payload += f"- **Description:** {custom_desc or v.description}\n"
            payload += "- **Enforcement Mode:** "
            payload += f"{rule.mode.value if rule else 'block'}\n"
            if rule and rule.rationale:
                payload += f"- **Architectural Rationale:** {rule.rationale}\n"

            context = self._fetch_code_context(v.file, v.line)
            if context:
                payload += "\n**Code Context:**\n```\n"
                payload += context
                payload += "\n```\n"

            payload += "\n"

        if truncated > 0:
            payload += (
                f"\n---\n**Note:** {truncated} additional violations "
                "truncated. Re-run `validate_architecture_compliance` "
                "after fixing these to surface remaining violations.\n"
            )

        payload += (
            "**Execution Directive:**\n"
            "1. Read the specified lines in the affected files.\n"
            "2. Refactor the code to eliminate the violation while "
            "preserving all existing business logic.\n"
            "3. Call `validate_architecture_compliance` with "
            "`execution_depth` incremented by 1 from your prior call. "
            "If depth exceeds 3, proceed with remaining violations "
            "flagged for manual review."
        )

        return RemediationResult(
            summary=f"Found {len(violations)} architectural violations.",
            violations_count=len(violations),
            handoff_prompt=payload,
        )

    def _fetch_code_context(
        self, filepath: str, line: int, context_lines: int = 5
    ) -> str:
        if not os.path.exists(filepath):
            return ""
        try:
            with open(filepath, encoding="utf-8") as f:
                lines = f.readlines()
            start = max(0, line - context_lines - 1)
            end = min(len(lines), line + context_lines)
            context = ""
            for i in range(start, end):
                prefix = "> " if i == line - 1 else "  "
                context += f"{prefix}{i + 1:4d} | {lines[i]}"
            return context
        except Exception as e:
            logger.warning("Failed to fetch code context", file=filepath, error=str(e))
            return ""
