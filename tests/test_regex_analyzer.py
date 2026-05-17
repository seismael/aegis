from aegis.infrastructure.regex_analyzer import RegexAnalyzer
from aegis.core.models.governance import EngineType, Rule, Severity, EnforcementMode


class TestRegexAnalyzer:
    """
    Test suite for the RegexAnalyzer.
    """

    def _make_rule(self, rid, pattern):
        return Rule(
            id=rid,
            description=f"Regex: {rid}",
            engine_type=EngineType.REGEX,
            query=pattern,
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
        )

    def test_detects_hardcoded_password(self):
        analyzer = RegexAnalyzer()
        rule = self._make_rule("no-hardcoded-secrets", r"password\s*=")
        content = (
            "username = 'admin'\n"
            "password = 'supersecret'\n"
            "host = 'localhost'\n"
        )
        violations = analyzer.analyze_file("config.py", content, [rule])
        assert len(violations) == 1
        assert violations[0].line == 2
        assert violations[0].rule_id == "no-hardcoded-secrets"

    def test_no_match_returns_empty(self):
        analyzer = RegexAnalyzer()
        rule = self._make_rule("no-secrets", r"api_key\s*=")
        content = "x = 1\ny = 2\n"
        violations = analyzer.analyze_file("safe.py", content, [rule])
        assert len(violations) == 0

    def test_multiple_matches_across_lines(self):
        analyzer = RegexAnalyzer()
        rule = self._make_rule("no-todo", r"TODO|FIXME")
        content = (
            "# TODO: implement this\n"
            "def foo(): pass\n"
            "# FIXME: this is broken\n"
        )
        violations = analyzer.analyze_file("code.py", content, [rule])
        assert len(violations) == 2
        assert violations[0].line == 1
        assert violations[1].line == 3

    def test_empty_query_skipped(self):
        analyzer = RegexAnalyzer()
        rule = Rule(
            id="no-query",
            description="No query",
            engine_type=EngineType.REGEX,
            query=None,
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
        )
        content = "anything"
        violations = analyzer.analyze_file("f.py", content, [rule])
        assert len(violations) == 0

    def test_unicode_content(self):
        analyzer = RegexAnalyzer()
        rule = self._make_rule("no-unicode", r"café")
        content = "order = 'café latte'\n"
        violations = analyzer.analyze_file("order.py", content, [rule])
        assert len(violations) == 1
        assert violations[0].line == 1
