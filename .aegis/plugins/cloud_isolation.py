"""
Aegis Plugin: Cloud Isolation Guard

Enforces strict hexagonal boundaries by ensuring that domain logic
is decoupled from cloud-provider SDKs (AWS, GCP, Azure).

Use-case: Enterprise-grade isolation of business logic from infrastructure providers.
"""

import re
from collections.abc import Callable
from typing import Any

from aegis.core.plugins import CustomAnalyzerInterface
from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.policy.models import Rule


class CloudIsolationPlugin(CustomAnalyzerInterface):
    """
    Detects 'Cloud Leaks' in domain layers.
    Specifically looks for boto3, google-cloud, azure-storage-blob, etc.
    """

    DEFAULT_CLOUD_SDKS = [
        r"boto3",
        r"botocore",
        r"google\.cloud",
        r"azure\.",
        r"kubernetes",
        r"docker",
    ]

    def analyze_file(
        self, file_path: str, content: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        violations: list[ArchitecturalViolation] = []

        # Filter for rules that explicitly invoke cloud isolation
        cloud_rules = [
            r
            for r in rules
            if r.id.startswith("cloud-isolation")
            or (r.metadata or {}).get("plugin") == "cloud-isolation"
        ]

        if not cloud_rules:
            return []

        for rule in cloud_rules:
            sdks = (rule.metadata or {}).get("sdks", self.DEFAULT_CLOUD_SDKS)

            for i, line in enumerate(content.splitlines(), 1):
                stripped = line.strip()
                if not (stripped.startswith("import ") or stripped.startswith("from ")):
                    continue

                for sdk in sdks:
                    if re.search(rf"\b{sdk}\b", stripped):
                        desc = (
                            f"Cloud Leak detected: '{sdk}' SDK imported in pure "
                            "domain layer. Business logic must be cloud-agnostic. "
                            "Move to an infrastructure adapter."
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
        def get_cloud_isolation_status() -> dict[str, Any]:
            """Returns the current status of the CloudIsolationPlugin."""
            return {
                "status": "active",
                "default_sdks_monitored": self.DEFAULT_CLOUD_SDKS,
                "scope": "Domain Layer (Hexagonal Isolation)",
            }

        return [get_cloud_isolation_status]


def register_analyzers() -> list[CustomAnalyzerInterface]:
    return [CloudIsolationPlugin()]
