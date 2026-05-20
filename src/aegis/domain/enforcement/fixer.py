"""
Auto-fix engine for Aegis architectural violations.
Uses line-level regex replacement to fix common, deterministic violations.
"""

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.policy.models import Rule

if TYPE_CHECKING:
    from aegis.domain.enforcement.ports import FixProposal


class FixResult:
    """Outcome of applying an auto-fix to a single violation."""

    def __init__(self, file: str, line: int, rule_id: str, fixed: bool, message: str):
        self.file = file
        self.line = line
        self.rule_id = rule_id
        self.fixed = fixed
        self.message = message


class RuleFixer(ABC):
    """Abstract fixer for a specific rule. Returns fixed line or None."""

    @property
    @abstractmethod
    def rule_id(self) -> str: ...

    @abstractmethod
    def fix_line(self, line: str, _rule: Rule) -> str | None:
        """Return the fixed line content, or None if no fix applies."""
        ...


# ---------------------------------------------------------------------------
# Concrete fixers
# ---------------------------------------------------------------------------


class BareExceptFixer(RuleFixer):
    """Replace bare `except:` with `except Exception:`."""

    rule_id = "bp-explicit-exceptions"

    _PATTERN = re.compile(r"^(\s*)except\s*:")

    def fix_line(self, line: str, _rule: Rule) -> str | None:
        m = self._PATTERN.match(line)
        if m:
            return f"{m.group(1)}except Exception:{line[len(m.group(0)) :]}"
        return None


class PrintToLoggerFixer(RuleFixer):
    """Replace `print(...)` with `logger.info(...)` at module level."""

    rule_id = "no-print-statements"

    _PATTERN = re.compile(r"^\s*print\(")

    def fix_line(self, line: str, _rule: Rule) -> str | None:
        if self._PATTERN.match(line):
            indent = re.match(r"^(\s*)", line).group(1)
            stripped = line.lstrip()
            # Preserve original line endings
            trailing = "\n" if stripped.endswith("\n") else ""
            body = re.sub(r"^print\(", "logger.info(", stripped.rstrip("\n\r"))
            return f"{indent}{body}{trailing}"
        return None


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class FixerRegistry:
    """Registry of rule fixers, keyed by rule ID."""

    def __init__(self):
        self._fixers: dict[str, RuleFixer] = {}

    def register(self, fixer: RuleFixer) -> None:
        self._fixers[fixer.rule_id] = fixer

    def get(self, rule_id: str) -> RuleFixer | None:
        return self._fixers.get(rule_id)

    def list_ids(self) -> list[str]:
        return list(self._fixers.keys())

    def generate_fix_proposals(
        self,
        violations: list[ArchitecturalViolation],
        rules_map: dict[str, Rule],
    ) -> list["FixProposal"]:
        """
        Innovation: Generates machine-readable diffs/proposals for violations.
        Does NOT modify any files.
        """
        from difflib import unified_diff

        from aegis.domain.enforcement.ports import FixProposal

        proposals: list[FixProposal] = []

        by_file: dict[str, list[ArchitecturalViolation]] = {}
        for v in violations:
            if self.get(v.rule_id) is not None:
                by_file.setdefault(v.file, []).append(v)

        for filepath, file_violations in by_file.items():
            path = Path(filepath)
            if not path.exists():
                continue

            try:
                original_content = path.read_text(encoding="utf-8")
                lines = original_content.splitlines(keepends=True)
                fixed_lines = list(lines)
            except OSError:
                continue

            modified = False
            for v in sorted(file_violations, key=lambda x: x.line, reverse=True):
                fixer = self.get(v.rule_id)
                rule = rules_map.get(v.rule_id)
                if not fixer or not rule:
                    continue

                idx = v.line - 1
                if 0 <= idx < len(fixed_lines):
                    fixed = fixer.fix_line(fixed_lines[idx], rule)
                    if fixed is not None:
                        fixed_lines[idx] = fixed
                        modified = True

            if modified:
                diff = "".join(
                    unified_diff(
                        lines,
                        fixed_lines,
                        fromfile=f"a/{filepath}",
                        tofile=f"b/{filepath}",
                    )
                )
                proposals.append(
                    FixProposal(
                        file=filepath,
                        diff=diff,
                        replacement_code="".join(fixed_lines),
                    )
                )

        return proposals

    def apply_fixes(
        self,
        violations: list[ArchitecturalViolation],
        rules_map: dict[str, Rule],
        dry_run: bool = False,
    ) -> list[FixResult]:
        """Apply auto-fixes to files for all fixable violations.

        Returns a list of FixResult describing what was (or would be) changed.
        When *dry_run* is True, files are not modified.
        """
        by_file: dict[str, list[ArchitecturalViolation]] = {}
        for v in violations:
            if self.get(v.rule_id) is not None:
                by_file.setdefault(v.file, []).append(v)

        results: list[FixResult] = []

        for filepath, file_violations in by_file.items():
            path = Path(filepath)
            if not path.exists():
                results.append(
                    FixResult(filepath, 0, "", False, f"File not found: {filepath}")
                )
                continue

            try:
                content = path.read_text(encoding="utf-8")
            except OSError as e:
                results.append(FixResult(filepath, 0, "", False, f"Cannot read: {e}"))
                continue

            lines = content.splitlines(keepends=True)
            modified = False

            for v in sorted(file_violations, key=lambda x: x.line, reverse=True):
                fixer = self.get(v.rule_id)
                if fixer is None:
                    continue
                rule = rules_map.get(v.rule_id)
                if rule is None:
                    continue

                idx = v.line - 1
                if idx < 0 or idx >= len(lines):
                    continue

                original = lines[idx]
                fixed = fixer.fix_line(original, rule)
                if fixed is not None:
                    lines[idx] = fixed
                    modified = True
                    results.append(
                        FixResult(
                            filepath,
                            v.line,
                            v.rule_id,
                            True,
                            f"Fixed at line {v.line}",
                        )
                    )

            if modified and not dry_run:
                try:
                    path.write_text("".join(lines), encoding="utf-8")
                except OSError as e:
                    results.append(
                        FixResult(filepath, 0, "", False, f"Cannot write: {e}")
                    )

        return results


# Global singleton registry
_REGISTRY = FixerRegistry()

# Module-level aliases for ergonomic imports
register = _REGISTRY.register
get_fixer = _REGISTRY.get
list_fixable_rule_ids = _REGISTRY.list_ids
apply_fixes = _REGISTRY.apply_fixes


# Register built-in fixers
register(BareExceptFixer())
register(PrintToLoggerFixer())
