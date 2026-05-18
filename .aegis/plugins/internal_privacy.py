"""
Aegis Plugin: Internal API Privacy Guard

Enforces encapsulation by ensuring that 'private' internal modules
are only consumed by authorized 'composition' modules.

Use-case: Managing internal boundaries in complex repositories.
"""

import os
import re
from collections.abc import Callable

from aegis.core.plugins import CustomAnalyzerInterface
from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.policy.models import Rule


class InternalPrivacyPlugin(CustomAnalyzerInterface):
    """
    Flags unauthorized imports of private internal modules.
    Configured via rule.metadata: 'private_module' and 'authorized_consumers'.
    """

    def analyze_file(
        self, file_path: str, content: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        violations: list[ArchitecturalViolation] = []
        rel_path = os.path.normpath(file_path).replace(os.sep, ".")

        privacy_rules = [
            r for r in rules if (r.metadata or {}).get("plugin") == "internal-privacy"
        ]

        if not privacy_rules:
            return []

        for rule in privacy_rules:
            meta = rule.metadata or {}
            private_module = meta.get("private_module")
            authorized_consumers = meta.get("authorized_consumers", [])

            if not private_module:
                continue

            # Skip if the current file is an authorized consumer
            if any(re.search(p, rel_path) for p in authorized_consumers):
                continue

            # Skip if the current file IS the private module itself
            if re.search(private_module, rel_path):
                continue

            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if not (stripped.startswith("import ") or stripped.startswith("from ")):
                    continue

                # Check if the private module is being imported
                if re.search(fr"\b{private_module}\b", stripped):
                    desc = (
                        f"Internal Privacy Violation: Module '{private_module}' "
                        f"is private. Importing it in '{rel_path}' is forbidden. "
                        f"Authorized: ({', '.join(authorized_consumers)})"
                    )
                    violations.append(
                        ArchitecturalViolation(
                            file=file_path,
                            line=i,
                            rule_id=rule.id,
                            description=desc,
                            severity=rule.severity.value,
                        )
                    )

        return violations

    @property
    def mcp_tools(self) -> list[Callable]:
        def get_privacy_report() -> str:
            """Returns a summary of internal privacy boundaries."""
            return "InternalPrivacyPlugin: active"

        return [get_privacy_report]


def register_analyzers() -> list[CustomAnalyzerInterface]:
    return [InternalPrivacyPlugin()]
