import json
import os
from typing import List, Set, Optional
from pydantic import BaseModel
from aegis.domain.evaluation.ports import ASTViolation

class BaselineViolation(BaseModel):
    file: str
    line: int
    rule_id: str
    signature: Optional[str] = None

class BaselineManager:
    """
    Manages the architectural technical debt ledger (.aegis/baseline.json).
    Uses structural signatures to prevent line-number drift.
    """

    def __init__(self, directory: str = ".aegis"):
        self.path = os.path.join(directory, "baseline.json")
        os.makedirs(directory, exist_ok=True)

    def save_baseline(self, violations: List[ASTViolation]) -> None:
        baseline = [
            BaselineViolation(
                file=v.file, 
                line=v.line, 
                rule_id=v.rule_id,
                signature=v.signature
            ).model_dump()
            for v in violations
        ]
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=2)

    def add_to_baseline(self, violation: ASTViolation) -> None:
        baseline = self.load_baseline_raw()
        new_entry = BaselineViolation(
            file=violation.file, 
            line=violation.line, 
            rule_id=violation.rule_id,
            signature=violation.signature
        ).model_dump()
        
        # Match by signature if available, otherwise fallback to file/line/rule
        if not any(self._match(b, violation) for b in baseline):
            baseline.append(new_entry)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(baseline, f, indent=2)

    def is_exempt(self, violation: ASTViolation) -> bool:
        if not os.path.exists(self.path):
            return False
            
        baseline = self.load_baseline_raw()
            
        for b in baseline:
            if self._match(b, violation):
                return True
        return False

    def _match(self, baseline_entry: dict, violation: ASTViolation) -> bool:
        """
        Determines if a violation matches a baseline entry.
        Prioritizes signature-based matching to resist line drift.
        """
        # 1. Signature match (Strongest)
        if baseline_entry.get("signature") and violation.signature:
            if baseline_entry["signature"] == violation.signature and baseline_entry["rule_id"] == violation.rule_id:
                return True
                
        # 2. File/Line/Rule fallback (Legacy)
        if baseline_entry["file"] == violation.file and \
           baseline_entry["rule_id"] == violation.rule_id and \
           baseline_entry["line"] == violation.line:
            return True
            
        return False

    def load_baseline_raw(self) -> List[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

from typing import Optional
