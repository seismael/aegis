import json
import os

from pydantic import BaseModel

from aegis.core.models.governance import Rule, RuleCategory
from aegis.domain.evaluation.ports import ArchitecturalViolation


class BaselineViolation(BaseModel):
    """A single entry in the architectural debt ledger (baseline.json)."""

    file: str
    line: int
    rule_id: str
    signature: str | None = None


class BaselineManager:
    """
    Manages the architectural technical debt ledger (.aegis/baseline.json).
    Uses structural signatures to prevent line-number drift.
    """

    def __init__(self, directory: str = ".aegis"):
        self.path = os.path.join(directory, "baseline.json")
        os.makedirs(directory, exist_ok=True)

    def save_baseline(self, violations: list[ArchitecturalViolation]) -> None:
        baseline = [
            BaselineViolation(
                file=v.file, line=v.line, rule_id=v.rule_id, signature=v.signature
            ).model_dump()
            for v in violations
        ]
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=2)

    def add_to_baseline(self, violation: ArchitecturalViolation) -> None:
        baseline = self.load_baseline_raw()
        new_entry = BaselineViolation(
            file=violation.file,
            line=violation.line,
            rule_id=violation.rule_id,
            signature=violation.signature,
        ).model_dump()

        # Match by signature if available, otherwise fallback to file/line/rule
        if not any(self._match(b, violation) for b in baseline):
            baseline.append(new_entry)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(baseline, f, indent=2)

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
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def prune_stale(self, active_rule_ids: set) -> int:
        """Remove baseline entries for rules that no longer exist."""
        if not os.path.exists(self.path):
            return 0
        with open(self.path, encoding="utf-8") as f:
            try:
                baseline = json.load(f)
            except json.JSONDecodeError:
                return 0
        before = len(baseline)
        baseline = [b for b in baseline if b.get("rule_id") in active_rule_ids]
        after = len(baseline)
        if before != after:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(baseline, f, indent=2)
        return before - after
