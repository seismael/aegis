import os
from pathlib import Path

import httpx
import structlog
import yaml

from aegis.core.models.governance import Rule

logger = structlog.get_logger()


class PolicyParser:
    """
    Structured parser for architectural governance rules.
    Loads and validates rules from .aegis/rules/ directory with remote inheritance.
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

        if not data:
            return []

        rules_data = []

        # 1. Handle remote policy inheritance
        if "extends" in data:
            remote_url = data["extends"]
            try:
                logger.info("Fetching remote governance policy", url=remote_url)
                response = httpx.get(remote_url, timeout=10.0)
                response.raise_for_status()
                remote_data = yaml.safe_load(response.text)
                if remote_data and "rules" in remote_data:
                    rules_data.extend(remote_data["rules"])
            except Exception as e:
                logger.error(
                    "Failed to fetch remote policy", url=remote_url, error=str(e)
                )

        # 2. Merge local rules (local overrides remote)
        if "rules" in data:
            # Overwrite rules with the same ID
            local_rules = data["rules"]
            remote_dict = {r.get("id"): r for r in rules_data}
            for lr in local_rules:
                remote_dict[lr.get("id")] = lr
            rules_data = list(remote_dict.values())

        if not rules_data:
            return []

        rules = []
        for r_data in rules_data:
            try:
                rules.append(Rule(**r_data))
            except Exception as e:
                logger.warning(
                    "Skipping invalid rule", rule_id=r_data.get("id"), error=str(e)
                )
                continue

        return rules

    def parse_directory(self, rules_dir: str) -> list[Rule]:
        """
        Scans a directory of .yaml rule packs and merges them into a single rule list.
        Each file's stem determines the default category if not explicitly set.
        """
        if not os.path.isdir(rules_dir):
            logger.info(
                "Rules directory not found, falling back to single file",
                directory=rules_dir,
            )
            return []

        all_rules: list[Rule] = []
        target_dir = Path(rules_dir)

        for yaml_file in sorted(target_dir.glob("*.*y*ml")):
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if not data or "rules" not in data:
                        continue

                    for rule_dict in data["rules"]:
                        # Infer category from filename if not explicitly set
                        if "category" not in rule_dict:
                            rule_dict["category"] = yaml_file.stem

                        try:
                            all_rules.append(Rule(**rule_dict))
                        except Exception as e:
                            logger.warning(
                                "Skipping invalid rule in pack",
                                file=yaml_file.name,
                                rule_id=rule_dict.get("id"),
                                error=str(e),
                            )
            except Exception as e:
                logger.error(
                    "Failed to parse rule pack", file=yaml_file.name, error=str(e)
                )

        logger.info("Loaded governance rules from directory", total=len(all_rules))
        return all_rules
