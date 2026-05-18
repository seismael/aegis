"""
Aegis plugin — Import Boundary Guard.

Enforces structural boundaries by scanning for forbidden cross-layer imports
(e.g., infrastructure leaking into domain).
"""

import os
import re
from collections.abc import Callable

from aegis.core.plugins import CustomAnalyzerInterface
from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.policy.models import Rule


class ImportBoundaryGuard(CustomAnalyzerInterface):
    """
    Flags forbidden imports between architectural layers.
    Configured via rule.metadata: source and target layer patterns.
    """

    def analyze_file(
        self, file_path: str, content: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        violations: list[ArchitecturalViolation] = []
        rel_path = os.path.normpath(file_path)

        for rule in rules:
            raw_src = (rule.metadata or {}).get("source", [])
            raw_tgt = (rule.metadata or {}).get("target", [])
            source_patterns = [raw_src] if isinstance(raw_src, str) else list(raw_src)
            target_patterns = [raw_tgt] if isinstance(raw_tgt, str) else list(raw_tgt)
            if not source_patterns or not target_patterns:
                continue

            if not any(p in rel_path for p in source_patterns):
                continue

            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if not stripped.startswith("import ") and not stripped.startswith(
                    "from "
                ):
                    continue
                for target in target_patterns:
                    if re.search(target, stripped):
                        violations.append(
                            ArchitecturalViolation(
                                file=file_path,
                                line=i,
                                rule_id=rule.id,
                                description=(
                                    f"Forbidden import in '{rel_path}': "
                                    f"matches target pattern '{target}'"
                                ),
                                severity=rule.severity.value,
                            )
                        )
        return violations

    @property
    def mcp_tools(self) -> list[Callable]:
        def custom_health_check() -> str:
            """Aegis plugin health check — returns status of ImportBoundaryGuard."""
            return "ImportBoundaryGuard: active"

        return [custom_health_check]


def register_analyzers() -> list[CustomAnalyzerInterface]:
    return [ImportBoundaryGuard()]
