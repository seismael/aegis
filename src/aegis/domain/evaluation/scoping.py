from pathlib import PurePosixPath

from aegis.core.models.governance import Rule
from aegis.domain.evaluation.ports import ArchitecturalViolation


class ScopeFilter:
    """
    Rule scoping filter: applies_to (positive) and excludes (negative) pattern
    matching against violation file paths.

    PurePosixPath.match() treats ** as a single path component, so
    patterns like "tests/**" don't match nested directories. The
    _path_matches_pattern method resolves ** to match all descendants.
    """

    @staticmethod
    def _path_matches_pattern(path: PurePosixPath, pattern: str) -> bool:
        """Match path against a glob pattern with recursive ** support."""
        if "**" not in pattern:
            return path.match(pattern)

        prefix = pattern.rsplit("**", 1)[0].rstrip("/")
        if not prefix:
            return True

        p = prefix + "/"
        path_str = str(path)
        return path_str.startswith(p) or p in path_str

    @staticmethod
    def filter_violations(
        violations: list[ArchitecturalViolation], rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        """
        Filter violations by rule scoping (applies_to / excludes).

        Keep violations whose file matches at least one `applies_to` pattern
        and does NOT match any `excludes` pattern for the violated rule.
        """
        rule_map = {r.id: r for r in rules}
        filtered: list[ArchitecturalViolation] = []

        for v in violations:
            rule = rule_map.get(v.rule_id)
            if not rule:
                filtered.append(v)
                continue

            pp = PurePosixPath(v.file.replace("\\", "/"))

            if rule.applies_to:
                allowed = any(
                    ScopeFilter._path_matches_pattern(pp, p) for p in rule.applies_to
                )
                if not allowed:
                    continue

            if rule.excludes:
                excluded = any(
                    ScopeFilter._path_matches_pattern(pp, p) for p in rule.excludes
                )
                if excluded:
                    continue

            filtered.append(v)

        return filtered
