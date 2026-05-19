from pathlib import PurePosixPath

from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.policy.models import Rule


class ScopeFilter:
    """
    Rule scoping filter: applies_to (positive) and excludes (negative) pattern
    matching against violation file paths.

    Supports glob patterns with ** for recursive matching.
    """

    @staticmethod
    def _path_matches_pattern(path: PurePosixPath, pattern: str) -> bool:
        """Match path against a glob pattern with recursive ** support."""
        if "**" not in pattern:
            return path.match(pattern)

        path_str = str(path)

        # Split on ** and strip surrounding slashes.
        segments = [s.strip("/") for s in pattern.split("**")]

        # Strip leading ./ from the first segment for normalization.
        if segments and segments[0].startswith("./"):
            segments[0] = segments[0][2:]

        # Pure ** or all-empty segments matches everything.
        if all(not s for s in segments):
            return True

        idx = 0

        for i, seg in enumerate(segments):
            if not seg:
                continue

            if i == 0:
                # First non-empty segment — search anywhere in the path
                # so that absolute paths (C:/dev/.../src/...) still
                # match relative patterns (src/**).
                found = path_str.find(seg)
                if found == -1:
                    return False
                idx = found + len(seg)
                continue

            if i == len(segments) - 1:
                # Last non-empty segment must be a suffix.
                if "*" in seg or "?" in seg or "[" in seg:
                    if not PurePosixPath(path_str).match(seg):
                        return False
                elif not path_str.endswith(seg):
                    return False
                continue

            # Middle segments must appear in order after the current position.
            found = path_str.find(seg, idx)
            if found == -1:
                return False
            idx = found + len(seg)

        return True

    @staticmethod
    def filter_violations(
        violations: list[ArchitecturalViolation], rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        """
        Filter violations by rule scoping (applies_to / excludes).

        Keep violations whose file matches at least one *applies_to* pattern
        and does NOT match any *excludes* pattern for the violated rule.
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

    @staticmethod
    def filter_rules_for_file(path: str, rules: list[Rule]) -> list[Rule]:
        """
        Returns the subset of rules whose scoping patterns match the given file path.

        A rule is relevant if *applies_to* (if set) matches the path and *excludes*
        (if set) does NOT match.
        """
        pp = PurePosixPath(path.replace("\\", "/"))
        matching: list[Rule] = []

        for rule in rules:
            if rule.applies_to:
                allowed = any(
                    ScopeFilter._path_matches_pattern(pp, p)
                    for p in rule.applies_to
                )
                if not allowed:
                    continue

            if rule.excludes:
                excluded = any(
                    ScopeFilter._path_matches_pattern(pp, p)
                    for p in rule.excludes
                )
                if excluded:
                    continue

            matching.append(rule)

        return matching
