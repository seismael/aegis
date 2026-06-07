from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.evaluation.scoping import ScopeFilter
from aegis.domain.policy.models import EnforcementMode, EngineType, Rule, Severity


class TestViolationScopeFiltering:
    """Test suite for ScopeFilter.filter_violations — rule scoping."""

    def _rule(self, rid, applies_to=None, excludes=None):
        return Rule(
            id=rid,
            description=f"Rule: {rid}",
            engine_type=EngineType.TREE_SITTER,
            query="(function_definition) @v",
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
            applies_to=applies_to or [],
            excludes=excludes or [],
        )

    def _violation(self, file, rule_id):
        return ArchitecturalViolation(
            file=file, line=1, rule_id=rule_id, description="test"
        )

    def test_passthrough_when_no_scoping_on_rule(self):
        """Violation kept when rule has no applies_to or excludes."""
        v = self._violation("src/main.py", "r1")
        result = ScopeFilter.filter_violations([v], [self._rule("r1")])
        assert len(result) == 1

    def test_applies_to_keeps_matching(self):
        """Violation kept when file matches applies_to."""
        v = self._violation("src/main.py", "r1")
        r = self._rule("r1", applies_to=["src/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 1

    def test_applies_to_filters_non_matching(self):
        """Violation filtered when file does not match applies_to."""
        v = self._violation("tests/test_main.py", "r1")
        r = self._rule("r1", applies_to=["src/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 0

    def test_excludes_filters_matching(self):
        """Violation filtered when file matches excludes."""
        v = self._violation("src/cli/main.py", "r1")
        r = self._rule("r1", excludes=["src/cli/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 0

    def test_excludes_keeps_non_matching(self):
        """Violation kept when file does not match excludes."""
        v = self._violation("src/core/main.py", "r1")
        r = self._rule("r1", excludes=["src/cli/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 1

    def test_applies_to_and_excludes_combined(self):
        """applies_to AND excludes both applied: must match one, not the other."""
        v_cli = self._violation("src/cli/main.py", "r1")
        v_core = self._violation("src/core/main.py", "r1")
        r = self._rule("r1", applies_to=["src/**"], excludes=["src/cli/**"])

        result = ScopeFilter.filter_violations([v_cli, v_core], [r])
        assert len(result) == 1
        assert result[0].file == "src/core/main.py"

    def test_unknown_rule_preserved(self):
        """Violations for unknown rules are preserved (defensive)."""
        v = self._violation("src/main.py", "unknown-rule")
        result = ScopeFilter.filter_violations([v], [self._rule("r1")])
        assert len(result) == 1

    def test_multiple_applies_to_any_match_suffices(self):
        """Violation kept if it matches ANY of the applies_to patterns."""
        v = self._violation("docs/guide.md", "r1")
        r = self._rule("r1", applies_to=["src/**", "docs/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 1

    def test_multiple_excludes_any_match_filters(self):
        """Violation filtered if it matches ANY of the excludes patterns."""
        v = self._violation("src/cli/main.py", "r1")
        r = self._rule("r1", excludes=["src/cli/**", "tests/**", "scripts/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 0

    def test_absolute_path_with_backslashes(self):
        """Windows-style absolute paths normalized and matched correctly."""
        v = self._violation("C:\\dev\\projects\\aegis\\src\\cli\\main.py", "r1")
        r = self._rule("r1", excludes=["src/cli/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 0

    def test_absolute_path_unix_style(self):
        """Unix-style absolute paths matched correctly."""
        v = self._violation("/home/user/project/tests/test_x.py", "r1")
        r = self._rule("r1", applies_to=["src/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 0

    def test_empty_violations_list(self):
        """Empty violations list returns empty list."""
        result = ScopeFilter.filter_violations([], [self._rule("r1")])
        assert result == []

    def test_empty_rules_list(self):
        """All violations preserved when no rules provided."""
        v = self._violation("src/main.py", "r1")
        result = ScopeFilter.filter_violations([v], [])
        assert len(result) == 1

    # --- ** edge cases ---

    def test_double_star_prefix_matches_nested(self):
        """Pattern prefix/** matches all descendants."""
        v = self._violation("src/a/b/c/main.py", "r1")
        r = self._rule("r1", applies_to=["src/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 1

    def test_double_star_between_matches_any_depth(self):
        """Pattern **/tests/** matches any file under a tests/ dir at any depth."""
        v = self._violation("src/tests/unit/test_x.py", "r1")
        r = self._rule("r1", applies_to=["**/tests/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 1

    def test_double_star_between_no_match(self):
        """Pattern **/tests/** does not match non-tests paths."""
        v = self._violation("src/lib/unit/test_x.py", "r1")
        r = self._rule("r1", applies_to=["**/tests/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 0

    def test_double_star_between_exclude(self):
        """Exclude pattern **/tests/** filters nested tests."""
        v = self._violation("src/tests/unit/test_x.py", "r1")
        r = self._rule("r1", excludes=["**/tests/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 0

    def test_double_star_standalone(self):
        """Standalone ** matches everything."""
        v = self._violation("any/deeply/nested/file.py", "r1")
        r = self._rule("r1", applies_to=["**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 1

    def test_double_star_suffix(self):
        """Pattern prefix/**/suffix matches paths that end with suffix."""
        v = self._violation("src/a/b/main.py", "r1")
        r = self._rule("r1", applies_to=["src/**/main.py"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 1

    def test_double_star_suffix_no_match(self):
        """Pattern prefix/**/suffix does not match wrong suffix."""
        v = self._violation("src/a/b/other.py", "r1")
        r = self._rule("r1", applies_to=["src/**/main.py"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 0

    # --- Single wildcard edge cases ---

    def test_single_star_matches_one_component(self):
        """Single * matches one path component (no /)."""
        v = self._violation("src/lib/main.py", "r1")
        r = self._rule("r1", applies_to=["src/*/main.py"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 1

    def test_single_star_no_match_nested(self):
        """Single * does not match nested components."""
        v = self._violation("src/a/b/main.py", "r1")
        r = self._rule("r1", applies_to=["src/*/main.py"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 0

    # --- Empty / edge case patterns ---

    def test_applies_to_none_list(self):
        """None/empty applies_to keeps all violations."""
        v = self._violation("src/main.py", "r1")
        r = self._rule("r1", applies_to=[])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 1

    def test_excludes_none_list(self):
        """None/empty excludes keeps all violations."""
        v = self._violation("src/main.py", "r1")
        r = self._rule("r1", excludes=[])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 1

    def test_leading_dot_slash_normalized(self):
        """Pattern with ./ prefix matches correctly."""
        v = self._violation("src/main.py", "r1")
        r = self._rule("r1", applies_to=["./src/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 1

    def test_pattern_with_wildcard_ext(self):
        """applies_to pattern with *.ext matches right extension."""
        v_ok = self._violation("src/main.py", "r1")
        v_bad = self._violation("src/main.js", "r1")
        r = self._rule("r1", applies_to=["**/*.py"])
        result = ScopeFilter.filter_violations([v_ok, v_bad], [r])
        assert len(result) == 1
        assert result[0].file == "src/main.py"

    def test_file_at_root_matches(self):
        """File at root can match root-level patterns."""
        v = self._violation("main.py", "r1")
        r = self._rule("r1", applies_to=["main.py"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 1

    def test_file_at_root_no_match(self):
        """File at root does not match directory-scoped patterns."""
        v = self._violation("main.py", "r1")
        r = self._rule("r1", applies_to=["src/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 0

    def test_exclude_overrides_applies_to(self):
        """exclude wins over applies_to when both match."""
        v = self._violation("src/cli/main.py", "r1")
        r = self._rule("r1", applies_to=["src/**"], excludes=["src/cli/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 0

    def test_multiple_applies_to_some_match(self):
        """Violation passes if it matches at least one applies_to."""
        v = self._violation("scripts/build.py", "r1")
        r = self._rule("r1", applies_to=["src/**", "scripts/**", "tests/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 1

    def test_multiple_excludes_any_match(self):
        """Violation filtered if it matches any exclude."""
        v = self._violation("src/generated/autogen.py", "r1")
        r = self._rule("r1", excludes=["src/generated/**", "build/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 0

    def test_carriage_return_normalized(self):
        """Backslash paths from Windows are normalized to forward slash."""
        v = self._violation("src\\cli\\main.py", "r1")
        r = self._rule("r1", applies_to=["src/**"])
        result = ScopeFilter.filter_violations([v], [r])
        assert len(result) == 1


class TestScopeFilterGetRelevantRules:
    """Test suite for ScopeFilter.filter_rules_for_file — JIT rule scoping."""

    def _rule(self, rid, language="python", applies_to=None, excludes=None):
        return Rule(
            id=rid,
            description=f"Rule: {rid}",
            engine_type=EngineType.TREE_SITTER,
            query="(function_definition) @v",
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
            language=language,
            applies_to=applies_to or [],
            excludes=excludes or [],
        )

    def test_language_mismatch_filters_out(self):
        """A .js file does not match py-only rules."""
        rules = [self._rule("r1", language="python")]
        result = ScopeFilter.filter_rules_for_file("src/app.js", rules)
        assert len(result) == 0

    def test_language_match_includes(self):
        """A .py file matches python rules."""
        rules = [self._rule("r1", language="python")]
        result = ScopeFilter.filter_rules_for_file("src/app.py", rules)
        assert len(result) == 1

    def test_path_scoping_narrows_results(self):
        """applies_to must match the file path."""
        rules = [
            self._rule("r1", applies_to=["src/**"]),
            self._rule("r2", applies_to=["tests/**"]),
        ]
        result = ScopeFilter.filter_rules_for_file("src/app.py", rules)
        assert len(result) == 1
        assert result[0].id == "r1"

    def test_max_rules_limit(self):
        """Results capped at max_rules."""
        rules = [self._rule(f"r{i}") for i in range(10)]
        result = ScopeFilter.filter_rules_for_file("src/app.py", rules, max_rules=4)
        assert len(result) == 4

    def test_proximity_scoping_adds_rules(self):
        """Adjacency-like scoping via all_rules param passes direct matches."""
        rules = [
            self._rule("r1", applies_to=["src/core/**"]),
            self._rule("r2", applies_to=["src/utils/**"]),
        ]
        result = ScopeFilter.filter_rules_for_file(
            "src/core/main.py", rules, rules, max_rules=5
        )
        assert len(result) == 1
        assert result[0].id == "r1"

    def test_excludes_in_get_relevant_rules(self):
        """excludes pattern filters rules in filter_rules_for_file."""
        rules = [
            self._rule("r1", applies_to=["src/**"], excludes=["src/generated/**"]),
        ]
        result = ScopeFilter.filter_rules_for_file("src/generated/autogen.py", rules)
        assert len(result) == 0

    def test_adjacency_none_returns_only_direct_matches(self):
        """Only direct path-scoped matches are returned."""
        rules = [
            self._rule("r1", applies_to=["src/core/**"]),
            self._rule("r2", applies_to=["src/utils/**"]),
        ]
        result = ScopeFilter.filter_rules_for_file("src/core/main.py", rules)
        assert len(result) == 1
        assert result[0].id == "r1"

    def test_filter_rules_for_file(self):
        """filter_rules_for_file returns matching rules for a path."""
        rules = [
            self._rule("r1", applies_to=["src/**"]),
            self._rule("r2", applies_to=["tests/**"]),
        ]
        result = ScopeFilter.filter_rules_for_file("src/main.py", rules)
        assert len(result) == 1
        assert result[0].id == "r1"


class TestScopeFilterUtilities:
    """Direct tests for ScopeFilter utility methods."""

    def test_resolve_language_py(self):
        assert ScopeFilter._resolve_language("src/main.py") == "python"

    def test_resolve_language_tsx(self):
        assert ScopeFilter._resolve_language("src/component.tsx") == "tsx"

    def test_resolve_language_unknown(self):
        assert ScopeFilter._resolve_language("src/main.cpp") == "cpp"

    def test_resolve_language_no_ext(self):
        assert ScopeFilter._resolve_language("Makefile") == ""
