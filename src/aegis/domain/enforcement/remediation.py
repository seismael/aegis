import os

import structlog

from aegis.domain.evaluation.ports import (
    ArchitecturalViolation,
    RemediationProviderInterface,
    RemediationResult,
    RuleAnalyzerInterface,
)
from aegis.domain.policy.models import Rule

logger = structlog.get_logger()


class RemediationPromptSynthesizer(RemediationProviderInterface):
    """
    The 'Hands-Off' Enforcement Engine.
    Converts mathematical AST violations into rigid, context-rich
    system prompts designed to be executed by native AI agents via MCP.
    """

    def __init__(self, extra_analyzers: list[RuleAnalyzerInterface] | None = None):
        self.extra_analyzers = extra_analyzers or []

    def generate_remediation(
        self, violations: list[ArchitecturalViolation], rules_map: dict[str, Rule]
    ) -> RemediationResult:
        if not violations:
            return RemediationResult(
                summary="No remediation required. Architecture is compliant.",
                violations_count=0,
                handoff_prompt="No remediation required.",
            )

        # Innovation: Generate machine-readable diffs for fixable violations
        from aegis.domain.enforcement.fixer import _REGISTRY as fixer_registry

        proposals = fixer_registry.generate_fix_proposals(violations, rules_map)

        payload = (
            "**AEGIS ARCHITECTURAL GOVERNANCE INTERVENTION**\n\n"
            "Your previous code generation violated the project's strict "
            "architectural invariants. You are required to immediately "
            "refactor the following files before proceeding.\n\n"
        )

        for v in violations:
            rule: Rule | None = rules_map.get(v.rule_id)
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

            # Custom Plugin Remediation
            custom_desc = None
            for extra in self.extra_analyzers:
                if hasattr(extra, "provide_remediation"):
                    custom_desc = extra.provide_remediation(v, rule)
                    if custom_desc:
                        break

            payload += f"- **Description:** {custom_desc or v.description}\n"
            payload += "- **Enforcement Mode:** "
            payload += f"{rule.mode.value if rule else 'unknown'}\n"
            if rule and rule.rationale:
                payload += f"- **Architectural Rationale:** {rule.rationale}\n"

            # Context Synthesis (RAG)
            context = self._fetch_code_context(v.file, v.line)
            if context:
                payload += "\n**Code Context:**\n```python\n"
                payload += context
                payload += "\n```\n"

            # Check if we have a machine-readable proposal for this file
            proposal = next((p for p in proposals if p.file == v.file), None)
            if proposal and proposal.diff:
                payload += "\n**Suggested Fix (Unified Diff):**\n```diff\n"
                payload += proposal.diff
                payload += "\n```\n"

            payload += "\n"

        payload += (
            "**Execution Directive:**\n"
            "1. Read the specified lines in the affected files.\n"
            "2. Refactor the code to eliminate the violation while "
            "preserving all existing business logic.\n"
            "3. Do not modify formatting or comments outside the "
            "targeted scope.\n"
            "4. Call the `validate_workspace` Meta-Tool "
            "again to verify your fix."
        )

        return RemediationResult(
            summary=f"Found {len(violations)} architectural violations.",
            violations_count=len(violations),
            proposals=proposals,
            handoff_prompt=payload,
        )

    def _fetch_code_context(
        self, filepath: str, line: int, context_lines: int = 5
    ) -> str:
        """Fetches the specific lines of code surrounding a violation."""
        if not os.path.exists(filepath):
            return ""

        try:
            with open(filepath, encoding="utf-8") as f:
                lines = f.readlines()

            start = max(0, line - context_lines - 1)
            end = min(len(lines), line + context_lines)

            # Format with line numbers for the AI
            context = ""
            for i in range(start, end):
                prefix = "> " if i == line - 1 else "  "
                context += f"{prefix}{i + 1:4d} | {lines[i]}"

            return context
        except Exception as e:
            logger.warning("Failed to fetch code context", file=filepath, error=str(e))
            return ""
