"""
Aegis Core Policy Registry & Loader.
Defines immutable Pydantic rule schemas and policy file loading logic.
"""

from pathlib import Path

from aegis.domain.policy.models import Rule, RuleCategory, Severity
from aegis.domain.policy.parser import PolicyParser


class RegistryLoader:
    """
    Loads and compiles declarative YAML governance rules into standard Pydantic Rule schemas.
    """

    @staticmethod
    def load(workspace_root: str = ".") -> list[Rule]:
        """Load all active rules from .aegis/rules in the target workspace."""
        parser = PolicyParser(workspace_root)
        return parser.parse_all()

    @staticmethod
    def load_from_file(file_path: str) -> list[Rule]:
        """Load rules from a specific YAML file."""
        from aegis.domain.policy.parser import PolicyParser

        path = Path(file_path)
        workspace = str(path.parent.parent.parent) if path.parent.name == "rules" else str(path.parent)
        parser = PolicyParser(workspace)
        return parser._parse_file(path)


__all__ = ["Rule", "RuleCategory", "Severity", "RegistryLoader"]
