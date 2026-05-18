"""
Aegis Plugin: Deprecation & Migration Oracle

Enforces technical debt management by flagging deprecated modules, 
functions, or patterns and providing high-fidelity migration paths.

Use-case: Managing complex migrations (e.g. requests -> httpx) and 
sunsetting legacy internal APIs in professional codebases.
"""

import os
import re
from collections.abc import Callable
from typing import Any

from aegis.core.plugins import CustomAnalyzerInterface
from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.policy.models import Rule


class DeprecationOraclePlugin(CustomAnalyzerInterface):
    """
    Detects usages of deprecated code.
    Configured via rule.metadata: 'deprecated_patterns' (regex list) 
    and 'migration_path' (advice string).
    """

    def analyze_file(
        self, file_path: str, content: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        violations: list[ArchitecturalViolation] = []
        
        oracle_rules = [
            r for r in rules 
            if (r.metadata or {}).get("plugin") == "deprecation-oracle"
        ]

        if not oracle_rules:
            return []

        for rule in oracle_rules:
            meta = rule.metadata or {}
            patterns = meta.get("deprecated_patterns", [])
            migration_path = meta.get("migration_path", "No migration path provided.")
            
            if not patterns:
                continue

            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                # Skip comments
                if stripped.startswith("#"):
                    continue

                for pattern in patterns:
                    if re.search(pattern, stripped):
                        violations.append(
                            ArchitecturalViolation(
                                file=file_path,
                                line=i,
                                rule_id=rule.id,
                                description=(
                                    f"DEPRECATED PATTERN: Found usage of '{pattern}'. "
                                    f"Migration Path: {migration_path}"
                                ),
                                severity=rule.severity.value,
                            )
                        )
        
        return violations

    @property
    def mcp_tools(self) -> list[Callable]:
        def get_deprecation_summary() -> str:
            """Returns a high-level summary of active deprecation & migration plans."""
            return "DeprecationOraclePlugin: monitoring legacy technical debt"

        return [get_deprecation_summary]


def register_analyzers() -> list[CustomAnalyzerInterface]:
    return [DeprecationOraclePlugin()]
