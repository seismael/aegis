import re
from typing import Dict, List, Optional
from aegis.domain.evaluation.ports import RegexAnalyzerInterface, ASTViolation
from aegis.core.models.governance import Rule


class RegexAnalyzer(RegexAnalyzerInterface):
    """
    Regex-based pattern analyzer.
    Evaluates file content against rules using compiled regex patterns.
    """

    def __init__(self):
        self._pattern_cache: Dict[str, Optional[re.Pattern]] = {}

    def analyze_file(
        self, file_path: str, content: str, rules: List[Rule]
    ) -> List[ASTViolation]:
        violations: List[ASTViolation] = []

        for rule in rules:
            if not rule.query:
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

    def _get_pattern(self, query: str) -> Optional[re.Pattern]:
        if query not in self._pattern_cache:
            try:
                self._pattern_cache[query] = re.compile(query)
            except re.error:
                self._pattern_cache[query] = None
        return self._pattern_cache[query]
