import os
import re

from aegis.core.models.governance import Rule
from aegis.domain.evaluation.ports import ASTViolation, RegexAnalyzerInterface

_LANG_EXT_MAP = {
    "py": ".py",
    "ts": ".ts",
    "tsx": ".tsx",
    "js": ".js",
    "jsx": ".jsx",
    "rs": ".rs",
}


class RegexAnalyzer(RegexAnalyzerInterface):
    """Regex-based pattern analyzer. Respects rule.language to only scan matching file extensions."""

    def __init__(self):
        self._pattern_cache: dict[str, re.Pattern | None] = {}

    def analyze_file(
        self, file_path: str, content: str, rules: list[Rule]
    ) -> list[ASTViolation]:
        violations: list[ASTViolation] = []
        ext = self._resolve_ext(file_path)

        for rule in rules:
            if not rule.query:
                continue
            if ext != rule.language:
                continue

            pattern = self._get_pattern(rule.query)
            if pattern is None:
                continue

            for match in pattern.finditer(content):
                line = content[: match.start()].count("\n") + 1
                violations.append(
                    ASTViolation(
                        file=file_path,
                        line=line,
                        rule_id=rule.id,
                        description=rule.description,
                        severity=rule.severity.value,
                    )
                )

        return violations

    def _get_pattern(self, query: str) -> re.Pattern | None:
        if query not in self._pattern_cache:
            try:
                self._pattern_cache[query] = re.compile(query)
            except re.error:
                self._pattern_cache[query] = None
        return self._pattern_cache[query]

    @staticmethod
    def _resolve_ext(file_path: str) -> str:
        """Map file extension to short language code used in rules."""
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        for lang, mapped_ext in _LANG_EXT_MAP.items():
            if ext == mapped_ext:
                return lang
        return ext.lstrip(".")
