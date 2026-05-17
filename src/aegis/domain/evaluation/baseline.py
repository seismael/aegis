import json
import os
from typing import List, Set
from pydantic import BaseModel
from aegis.domain.evaluation.ports import ASTViolation

class BaselineViolation(BaseModel):
    file: str
    line: int
    rule_id: str

class BaselineManager:
    """
    Manages the architectural technical debt ledger (.aegis/baseline.json).
    Allows legacy violations to be exempted from active enforcement.
    """

    def __init__(self, directory: str = ".aegis"):
        self.path = os.path.join(directory, "baseline.json")
        os.makedirs(directory, exist_ok=True)

    def save_baseline(self, violations: List[ASTViolation]) -> None:
        baseline = [
            BaselineViolation(file=v.file, line=v.line, rule_id=v.rule_id).model_dump()
            for v in violations
        ]
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(baseline, f, indent=2)

    def add_to_baseline(self, violation: ASTViolation) -> None:
        baseline = self.load_baseline_raw()
        new_entry = BaselineViolation(file=violation.file, line=violation.line, rule_id=violation.rule_id).model_dump()
        
        # Check if already exists to avoid duplicates
        if not any(b["file"] == violation.file and b["rule_id"] == violation.rule_id and b["line"] == violation.line for b in baseline):
            baseline.append(new_entry)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(baseline, f, indent=2)

    def is_exempt(self, violation: ASTViolation) -> bool:
        if not os.path.exists(self.path):
            return False
            
        baseline = self.load_baseline_raw()
            
        for b in baseline:
            # Match by file and rule_id (line numbers can be fuzzy in production, 
            # but for this demo we'll use exact match)
            if b["file"] == violation.file and b["rule_id"] == violation.rule_id and b["line"] == violation.line:
                return True
        return False

    def load_baseline_raw(self) -> List[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)
