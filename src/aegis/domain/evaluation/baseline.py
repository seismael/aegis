import json
import os
import threading
from datetime import UTC, datetime

import structlog
from pydantic import BaseModel

from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.policy.models import Rule, RuleCategory

logger = structlog.get_logger()


class BaselineViolation(BaseModel):
    """A single entry in the architectural debt ledger (baseline.json)."""

    file: str
    line: int
    rule_id: str
    signature: str | None = None
    captured_at: str | None = None


class BaselineManager:
    """
    Manages the architectural technical debt ledger (.aegis/baseline.json).
    Uses structural signatures to prevent line-number drift.
    Thread-safe with file locking and atomic writes.
    """

    def __init__(self, directory: str = ".aegis"):
        self.path = os.path.join(directory, "baseline.json")
        self._lock = threading.Lock()
        # Do NOT create the directory in __init__ — let callers handle that.
        # The directory will be created on first write if needed.

    def _atomic_write(self, data: list) -> None:
        """Write data atomically: write to .tmp then os.replace."""
        tmp = self.path + ".tmp"
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, self.path)

    def save_baseline(self, violations: list[ArchitecturalViolation]) -> None:
        now = datetime.now(UTC).isoformat()
        baseline = [
            BaselineViolation(
                file=v.file,
                line=v.line,
                rule_id=v.rule_id,
                signature=v.signature,
                captured_at=now,
            ).model_dump()
            for v in violations
        ]
        with self._lock:
            self._atomic_write(baseline)

    def add_to_baseline(self, violation: ArchitecturalViolation) -> None:
        self.add_all_to_baseline([violation])

    def add_all_to_baseline(self, violations: list[ArchitecturalViolation]) -> None:
        if not violations:
            return

        with self._lock:
            baseline = self.load_baseline_raw()
            if len(baseline) >= 50_000:
                logger.warning(
                    "Baseline has grown unusually large",
                    size=len(baseline),
                    hint="Use evolve_ruleset(action='suppress') to prune stale entries",
                )

            now = datetime.now(UTC).isoformat()
            modified = False
            for v in violations:
                if not any(self._match(b, v) for b in baseline):
                    new_entry = BaselineViolation(
                        file=v.file,
                        line=v.line,
                        rule_id=v.rule_id,
                        signature=v.signature,
                        captured_at=now,
                    ).model_dump()
                    baseline.append(new_entry)
                    modified = True

            if modified:
                self._atomic_write(baseline)

    def is_exempt(
        self, violation: ArchitecturalViolation, rule: Rule | None = None
    ) -> bool:
        """
        Evaluates if a violation is grandfathered into the technical debt ledger.
        SECURITY rules strictly bypass the baseline and are never exempt.
        """
        # Zero-tolerance: security violations never exempt
        if rule is not None and rule.category == RuleCategory.SECURITY:
            return False

        if not os.path.exists(self.path):
            return False

        baseline = self.load_baseline_raw()

        for b in baseline:
            if self._match(b, violation):
                return True
        return False

    def _match(self, baseline_entry: dict, violation: ArchitecturalViolation) -> bool:
        """
        Determines if a violation matches a baseline entry.
        Uses structural signature matching when available;
        falls back to file/line/rule for violations without signatures.
        """
        if not isinstance(baseline_entry, dict):
            return False
        rid = baseline_entry.get("rule_id")
        sig = baseline_entry.get("signature") or None

        if sig:
            if not violation.signature:
                return False
            return sig == violation.signature and rid == violation.rule_id

        return (
            baseline_entry.get("file") == violation.file
            and rid == violation.rule_id
            and baseline_entry.get("line") == violation.line
        )

    def load_baseline_raw(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding="utf-8") as f:
            try:
                data = json.load(f)
                if not isinstance(data, list):
                    logger.warning("Baseline file is not a list, resetting")
                    return []
                return data
            except (json.JSONDecodeError, ValueError):
                logger.warning("Baseline file corrupted, resetting")
                return []

    def prune_stale(self, active_rule_ids: set) -> int:
        """Remove baseline entries for rules that no longer exist."""
        with self._lock:
            baseline = self.load_baseline_raw()
            if not baseline:
                return 0
            before = len(baseline)
            baseline = [
                b
                for b in baseline
                if isinstance(b, dict) and b.get("rule_id") in active_rule_ids
            ]
            after = len(baseline)
            if before != after:
                self._atomic_write(baseline)
        return before - after

    def show_baseline(self) -> str:
        """Return a human-readable summary of the baseline ledger."""
        baseline = self.load_baseline_raw()
        if not baseline:
            return "No baselined violations."
        counts: dict[str, int] = {}
        for b in baseline:
            rid = b.get("rule_id", "unknown")
            counts[rid] = counts.get(rid, 0) + 1
        lines = [f"Total baselined violations: {len(baseline)}\n"]
        for rid in sorted(counts):
            c = counts[rid]
            label = "entry" if c == 1 else "entries"
            lines.append(f"  {rid}: {c} {label}")
        return "\n".join(lines)

    def expire_old(self, days: int, active_rule_ids: set | None = None) -> int:
        """Remove baseline entries older than N days.

        Only applies age-based expiry to entries for currently active rules.
        Entries for deleted/unknown rules are preserved regardless of age.
        """
        with self._lock:
            baseline = self.load_baseline_raw()
            if not baseline:
                return 0
            before = len(baseline)
            cutoff = datetime.now(UTC)
            kept = []
            for b in baseline:
                if not isinstance(b, dict):
                    continue
                # Preserve entries for deleted rules regardless of age
                if (
                    active_rule_ids is not None
                    and b.get("rule_id") not in active_rule_ids
                ):
                    kept.append(b)
                    continue
                captured = b.get("captured_at")
                if captured:
                    try:
                        captured_dt = datetime.fromisoformat(captured)
                        age_days = (cutoff - captured_dt).days
                        if age_days > days:
                            continue  # expired
                    except (ValueError, TypeError):
                        pass  # keep entries with unparseable timestamps
                elif active_rule_ids is not None:
                    # No timestamp — treat as expired for active rules
                    continue
                kept.append(b)

            after = len(kept)
            if before != after:
                self._atomic_write(kept)
        return before - after
