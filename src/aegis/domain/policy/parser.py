import os
import yaml
from typing import List, Optional
from aegis.core.models.governance import Rule, Severity, EnforcementMode

class PolicyParser:
    """
    Structured parser for architectural governance rules.
    Loads and validates rules from .aegis/rules.yaml.
    """

    def parse_rules(self, rules_path: Optional[str] = None) -> List[Rule]:
        """
        Loads rules from the structured YAML definition.
        """
        if rules_path is None:
            # Try to find it in the current project root
            rules_path = self._discover_rules_file()
            
        if not rules_path or not os.path.exists(rules_path):
            return []
            
        with open(rules_path, "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
            except yaml.YAMLError:
                return []
            
        if not data or "rules" not in data:
            return []
            
        rules = []
        for r_data in data["rules"]:
            try:
                rules.append(Rule(**r_data))
            except Exception:
                # Log invalid rules in a real production system
                continue
                
        return rules

    def _discover_rules_file(self) -> Optional[str]:
        current = os.getcwd()
        while current != os.path.dirname(current):
            path = os.path.join(current, ".aegis", "rules.yaml")
            if os.path.exists(path):
                return path
            current = os.path.dirname(current)
        return None
