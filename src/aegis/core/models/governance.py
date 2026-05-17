from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class EnforcementMode(str, Enum):
    SILENT = "silent"
    REPORT = "report"
    WARN = "warn"
    BLOCK = "block"
    FIX = "fix"

class Rule(BaseModel):
    """
    The 'Logical Constraint' that defines an architectural invariant.
    """
    id: str
    description: str
    severity: Severity = Severity.HIGH
    mode: EnforcementMode = EnforcementMode.BLOCK

    # Language-specific query
    query: Optional[str] = None
    language: str = "py"

    # For positive rules (X must have Y): violations = candidates - check
    candidates_query: Optional[str] = None
    check_query: Optional[str] = None

    # Scoping
    applies_to: List[str] = Field(default_factory=lambda: ["**/*.py"])
    excludes: List[str] = Field(default_factory=list)

    # Ownership
    owner: Optional[str] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)
