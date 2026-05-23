from aegis.domain.evaluation.analyzers.regex import RegexAnalyzer
from aegis.domain.policy.models import EnforcementMode, EngineType, Rule, Severity


class TestRegexAnalyzer:
    """Test suite for the RegexAnalyzer."""

    def _make_rule(self, rid, pattern, language="py"):
        return Rule(
            id=rid,
            description=f"Regex: {rid}",
            engine_type=EngineType.REGEX,
            query=pattern,
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
            language=language,
        )

    def test_detects_hardcoded_password(self):
        analyzer = RegexAnalyzer()
        rule = self._make_rule("no-hardcoded-secrets", r"password\s*=")
        content = "username = 'admin'\npassword = 'supersecret'\nhost = 'localhost'\n"
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
        content = "# TODO: implement this\ndef foo(): pass\n# FIXME: this is broken\n"
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
        content = "order = 'café'\n"
        violations = analyzer.analyze_file("order.py", content, [rule])
        assert len(violations) == 1
        assert violations[0].line == 1

    # --- Language filtering ---

    def test_language_filter_skips_wrong_extension(self):
        """Rule with language='ts' is not applied to a .py file."""
        analyzer = RegexAnalyzer()
        rule = self._make_rule("r1", r"TODO", language="ts")
        violations = analyzer.analyze_file("main.py", "# TODO", [rule])
        assert violations == []

    def test_language_filter_applied_to_matching_extension(self):
        """Rule with language='ts' applied to .ts file."""
        analyzer = RegexAnalyzer()
        rule = self._make_rule("r1", r"TODO", language="ts")
        violations = analyzer.analyze_file("main.ts", "# TODO", [rule])
        assert len(violations) == 1

    # --- Invalid regex resilience ---

    def test_invalid_regex_does_not_crash(self):
        """Invalid regex pattern is cached as None, no crash."""
        analyzer = RegexAnalyzer()
        rule = self._make_rule("r1", r"\x_invalid")
        violations = analyzer.analyze_file("f.py", "x = 1", [rule])
        assert violations == []

    def test_invalid_regex_cached(self):
        """Invalid regex is cached to avoid repeated compile attempts."""
        analyzer = RegexAnalyzer()
        rule = self._make_rule("r1", r"\x_invalid")
        analyzer.analyze_file("f.py", "x = 1", [rule])
        assert analyzer._pattern_cache.get(r"\x_invalid") is None

    # --- Pattern caching ---

    def test_pattern_cache_hit(self):
        """Same pattern reused across rules uses cached compiled regex."""
        analyzer = RegexAnalyzer()
        rule_a = self._make_rule("r1", r"TODO")
        rule_b = self._make_rule("r2", r"TODO")
        analyzer.analyze_file("a.py", "# TODO", [rule_a])
        analyzer.analyze_file("b.py", "# TODO", [rule_b])
        # Only one entry in cache
        assert len(analyzer._pattern_cache) == 1

    # --- _resolve_ext ---

    def test_resolve_ext_known(self):
        """Known extensions map to language codes."""
        assert RegexAnalyzer._resolve_ext("main.py") == "py"
        assert RegexAnalyzer._resolve_ext("app.ts") == "ts"
        assert RegexAnalyzer._resolve_ext("app.tsx") == "tsx"
        assert RegexAnalyzer._resolve_ext("app.js") == "js"
        assert RegexAnalyzer._resolve_ext("app.jsx") == "jsx"
        assert RegexAnalyzer._resolve_ext("lib.rs") == "rs"

    def test_resolve_ext_unknown(self):
        """Unknown extensions return the extension without leading dot."""
        assert RegexAnalyzer._resolve_ext("file.xyz") == "xyz"
        assert RegexAnalyzer._resolve_ext(".hidden") == ""

    def test_resolve_ext_no_extension(self):
        """Files without extension return empty string."""
        assert RegexAnalyzer._resolve_ext("Makefile") == ""
        assert RegexAnalyzer._resolve_ext("Dockerfile") == ""

    # --- Edge cases ---

    def test_empty_content(self):
        """Empty content produces no violations."""
        analyzer = RegexAnalyzer()
        rule = self._make_rule("r1", r".")
        violations = analyzer.analyze_file("f.py", "", [rule])
        assert violations == []

    def test_match_at_first_line(self):
        """Match on first line reports line 1."""
        analyzer = RegexAnalyzer()
        rule = self._make_rule("r1", r"START")
        violations = analyzer.analyze_file("f.py", "START HERE\n", [rule])
        assert len(violations) == 1
        assert violations[0].line == 1

    def test_match_on_last_line_no_newline(self):
        """Match on final line without trailing newline."""
        analyzer = RegexAnalyzer()
        rule = self._make_rule("r1", r"END")
        violations = analyzer.analyze_file("f.py", "line1\nline2\nEND", [rule])
        assert len(violations) == 1
        assert violations[0].line == 3

    def test_multiple_rules_on_same_file(self):
        """Multiple regex rules applied to one file."""
        analyzer = RegexAnalyzer()
        rules = [
            self._make_rule("no-todo", r"TODO"),
            self._make_rule("no-bug", r"BUG"),
        ]
        content = "TODO: fix this\nBUG: here\n"
        violations = analyzer.analyze_file("f.py", content, rules)
        assert len(violations) == 2
        assert {v.rule_id for v in violations} == {"no-todo", "no-bug"}

    def test_case_sensitive_by_default(self):
        """Regex is case-sensitive by default."""
        analyzer = RegexAnalyzer()
        rule = self._make_rule("r1", r"todo")
        violations = analyzer.analyze_file("f.py", "TODO\n", [rule])
        assert violations == []

    def test_zero_length_match_does_not_infinite_loop(self):
        """Zero-length match (e.g. `.?`) doesn't cause issues."""
        analyzer = RegexAnalyzer()
        rule = self._make_rule("r1", r".?")
        violations = analyzer.analyze_file("f.py", "abc\n", [rule])
        # Should not infinite-loop; returns some matches
        assert isinstance(violations, list)
