import json
import os
import threading
from collections import Counter
from datetime import UTC, datetime


class TelemetryRecorder:
    """Persists and aggregates architectural telemetry to .aegis/telemetry.json."""

    def __init__(self, workspace_root: str):
        self.root_dir = workspace_root
        self.path = os.path.join(workspace_root, ".aegis", "telemetry.json")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._lock = threading.Lock()

    def record_remediation(self, rule_id: str, timestamp: str | None = None) -> None:
        """Log a single apply_architectural_remediation call."""
        data = self._load()
        data.setdefault("remediations", []).append(
            {
                "rule_id": rule_id,
                "timestamp": (timestamp or datetime.now(UTC).isoformat()),
            }
        )
        self._save(data)

    def record_check(
        self,
        total_violations: int,
        active_violations: int,
        timestamp: str | None = None,
    ) -> None:
        """Record a compliance check event."""
        import json
        from datetime import datetime
        from pathlib import Path

        telemetry_path = Path(self.root_dir) / ".aegis" / "telemetry.json"
        telemetry_dir = telemetry_path.parent
        telemetry_dir.mkdir(parents=True, exist_ok=True)

        data = []
        if telemetry_path.exists():
            try:
                data = json.loads(telemetry_path.read_text())
            except (json.JSONDecodeError, FileNotFoundError):
                data = []

        if not isinstance(data, list):
            data = []

        data.append(
            {
                "timestamp": timestamp or datetime.now(UTC).isoformat(),
                "total_violations": total_violations,
                "active_violations": active_violations,
                "type": "check",
            }
        )

        telemetry_path.write_text(json.dumps(data, indent=2))

    def get_insights(self) -> dict:
        """Aggregate telemetry into a scorecard dict."""
        data = self._load()
        remediations = data.get("remediations", [])
        checks = data.get("checks", [])

        rule_counter = Counter(r["rule_id"] for r in remediations)

        success = sum(1 for c in checks if c["violation_count"] == 0)
        total_violations = sum(c["violation_count"] for c in checks)

        return {
            "total_remediations": len(remediations),
            "total_checks": len(checks),
            "remediation_by_rule": dict(rule_counter.most_common(10)),
            "check_success_rate": (success / len(checks) if checks else 0.0),
            "avg_violations_per_check": (
                total_violations / len(checks) if checks else 0.0
            ),
            "total_violations_found": total_violations,
        }

    def display_insights(self) -> str:
        """Return a human-readable scorecard string."""
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

    def _load(self) -> dict:
        """Thread-safe load from disk."""
        if not os.path.exists(self.path):
            return {}
        with self._lock:
            try:
                with open(self.path, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                return {}

    def _save(self, data: dict) -> None:
        """Thread-safe save to disk."""
        with self._lock:
            try:
                with open(self.path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except OSError:
                pass
