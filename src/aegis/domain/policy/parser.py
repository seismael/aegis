import os
from pathlib import Path

import httpx
import structlog
import yaml

from aegis.domain.policy.models import Rule, RuleCategory

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

    def _validate_pack_directories(self, rules_dir: Path) -> None:
        """Warn about subdirectory names that don't match any RuleCategory value."""
        valid = {m.value for m in RuleCategory}
        bad_dirs: list[str] = []
        for entry in sorted(rules_dir.iterdir()):
            if not entry.is_dir() or entry.name in valid:
                continue
            # Only flag directories that actually contain rule files
            if not any(f.suffix in (".yaml", ".yml") for f in entry.rglob("*")):
                continue
            # Check if any rule file in this dir relies on category inference
            # (i.e., lacks an explicit 'category' field)
            has_implicit = False
            for yf in entry.rglob("*.*y*ml"):
                if yf.name == "pack.yaml":
                    continue
                try:
                    with open(yf, encoding="utf-8") as fh:
                        yd = yaml.safe_load(fh)
                        if yd and "rules" in yd:
                            for r in yd["rules"]:
                                if "category" not in r:
                                    has_implicit = True
                                    break
                    if has_implicit:
                        break
                except Exception:
                    continue
            if has_implicit:
                bad_dirs.append(entry.name)

        if bad_dirs:
            fix_hint = (
                "Rename to match a valid category or"
                " add 'category: <valid>' to each rule"
            )
            logger.warning(
                "Rule pack directories with names that don't match any RuleCategory — "
                "rules without explicit 'category' field won't parse",
                directories=bad_dirs,
                valid_categories=sorted(valid),
                fix=fix_hint,
            )

    def _warn_duplicate_ids(self, rules: list[Rule]) -> None:
        """Warn about duplicate rule IDs across loaded packs."""
        seen: dict[str, list[str]] = {}
        for r in rules:
            seen.setdefault(r.id, []).append(r.description)
        dupes = {k: v for k, v in seen.items() if len(v) > 1}
        if dupes:
            logger.warning(
                "Duplicate rule IDs detected — only the last-loaded version wins",
                duplicates={k: len(v) for k, v in dupes.items()},
            )

    def parse_directory(self, rules_dir: str) -> list[Rule]:
        """
        Scans a directory of .yaml rule packs (recursively) and merges them into
        a single rule list.  Rules inside a subdirectory get their default category
        from the parent directory name; rules at the root level get it from the
        filename stem.
        """
        if not os.path.isdir(rules_dir):
            logger.info(
                "Rules directory not found, falling back to single file",
                directory=rules_dir,
            )
            return []

        all_rules: list[Rule] = []
        target_dir = Path(rules_dir)

        # Validate directory names against RuleCategory enum
        self._validate_pack_directories(target_dir)

        for yaml_file in sorted(target_dir.rglob("*.*y*ml")):
            if yaml_file.name == "pack.yaml":
                continue

            try:
                with open(yaml_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if not data or "rules" not in data:
                        continue

                    for rule_dict in data["rules"]:
                        if "category" not in rule_dict:
                            parent = yaml_file.parent
                            # If file is inside a subdirectory of rules_dir, use
                            # the subdirectory name  (e.g.  architecture/rules.yaml
                            # → category: architecture).  Otherwise use the stem.
                            if parent != target_dir:
                                rule_dict["category"] = parent.name
                            else:
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

        self._warn_duplicate_ids(all_rules)

        logger.info("Loaded governance rules from directory", total=len(all_rules))
        return all_rules
