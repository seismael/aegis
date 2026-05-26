import json
import os
import threading
from collections import Counter
from datetime import UTC, datetime

from aegis.domain.observability.telemetry import TelemetryExporterInterface


class LocalJSONExporter(TelemetryExporterInterface):
    """Persists telemetry events to a local JSON file."""

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        self._lock = threading.Lock()

    def record_remediation(self, rule_id: str, timestamp: str | None = None) -> None:
        with self._lock:
            data = self._load_unlocked()
            data.setdefault("remediations", []).append(
                {
                    "rule_id": rule_id,
                    "timestamp": timestamp or datetime.now(UTC).isoformat(),
                }
            )
            self._save_unlocked(data)

    def record_check(
        self,
        total_violations: int,
        active_violations: int,
        timestamp: str | None = None,
    ) -> None:
        with self._lock:
            data = self._load_unlocked()
            data.setdefault("checks", []).append(
                {
                    "timestamp": timestamp or datetime.now(UTC).isoformat(),
                    "violation_count": total_violations,
                    "active_violations": active_violations,
                    "type": "check",
                }
            )
            self._save_unlocked(data)

    def get_insights(self) -> dict:
        with self._lock:
            data = self._load_unlocked()
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

    def _load_unlocked(self) -> dict:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_unlocked(self, data: dict) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass
