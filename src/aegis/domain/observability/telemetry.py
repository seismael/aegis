import os
from abc import ABC, abstractmethod


class TelemetryExporterInterface(ABC):
    """Generic telemetry sink for architectural observability."""

    @abstractmethod
    def record_check(
        self,
        total_violations: int,
        active_violations: int,
        timestamp: str | None = None,
    ) -> None:
        """Record a compliance check event."""
        ...

    @abstractmethod
    def record_remediation(
        self,
        rule_id: str,
        timestamp: str | None = None,
    ) -> None:
        """Log a single remediation call."""
        ...

    @abstractmethod
    def get_insights(self) -> dict:
        """Aggregate telemetry into a scorecard dict."""
        ...


class TelemetryRecorder:
    """
    Facade over a TelemetryExporterInterface.
    Delegates persistence to the exporter; adds display formatting and
    config-driven exporter resolution.
    """

    def __init__(
        self,
        workspace_root: str,
        exporter: TelemetryExporterInterface | None = None,
    ):
        self.root_dir = workspace_root
        self._exporter = exporter or self._resolve_exporter(workspace_root)

    def record_remediation(self, rule_id: str, timestamp: str | None = None) -> None:
        self._exporter.record_remediation(rule_id, timestamp)

    def record_check(
        self,
        total_violations: int,
        active_violations: int,
        timestamp: str | None = None,
    ) -> None:
        self._exporter.record_check(total_violations, active_violations, timestamp)

    def get_insights(self) -> dict:
        return self._exporter.get_insights()

    def display_insights(self) -> str:
        insights = self.get_insights()
        lines = ["## Aegis Insights Scorecard\n"]
        lines.append(f"- **Total checks run:** {insights['total_checks']}")
        lines.append(
            f"- **Total remediations applied: {insights['total_remediations']}**"
        )
        lines.append(f"- **Check success rate: {insights['check_success_rate']:.0%}**")
        lines.append(
            "- **Avg violations per check:"
            f" {insights['avg_violations_per_check']:.1f}**"
        )
        lines.append(
            f"- **Total violations found: {insights['total_violations_found']}**"
        )
        if insights["remediation_by_rule"]:
            lines.append("\n### Most Remediated Rules\n")
            for rid, count in insights["remediation_by_rule"].items():
                lines.append(f"- **{rid}:** {count} remediations")
        return "\n".join(lines)

    @staticmethod
    def _resolve_exporter(workspace_root: str) -> TelemetryExporterInterface:
        from aegis.domain.observability.exporters.local import LocalJSONExporter

        telemetry_path = os.path.join(workspace_root, ".aegis", "telemetry.json")
        return LocalJSONExporter(telemetry_path)
