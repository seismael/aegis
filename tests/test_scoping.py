from aegis.core.models.governance import EnforcementMode, EngineType, Rule, Severity
from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.evaluation.scoping import ScopeFilter


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
