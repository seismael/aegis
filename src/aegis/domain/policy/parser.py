import os

import yaml

from aegis.core.models.governance import Rule


class PolicyParser:
    """
    Structured parser for architectural governance rules.
    Loads and validates rules from .aegis/rules.yaml.
    """

    def parse_rules(self, rules_path: str) -> list[Rule]:
        """
        Loads rules from the structured YAML definition.
        """
        if not os.path.exists(rules_path):
            return []

        with open(rules_path, encoding="utf-8") as f:
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

