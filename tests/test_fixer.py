"""Tests for the auto-fix engine."""

from aegis.domain.enforcement.fixer import (
    BareExceptFixer,
    PrintToLoggerFixer,
    apply_fixes,
    get_fixer,
    list_fixable_rule_ids,
    register,
)
from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.policy.models import Rule


class TestBareExceptFixer:
    def setup_method(self):
        self.fixer = BareExceptFixer()
        self.rule = Rule(id="bp-explicit-exceptions", description="test")

    def test_fixes_bare_except(self):
        result = self.fixer.fix_line("except:\n", self.rule)
        assert result == "except Exception:\n"

    def test_fixes_indented_except(self):
        result = self.fixer.fix_line("    except:\n", self.rule)
        assert result == "    except Exception:\n"

    def test_leaves_typed_except(self):
        result = self.fixer.fix_line("except ValueError:\n", self.rule)
        assert result is None

    def test_leaves_irrelevant_line(self):
        result = self.fixer.fix_line("def foo():\n", self.rule)
        assert result is None


class TestPrintToLoggerFixer:
    def setup_method(self):
        self.fixer = PrintToLoggerFixer()
        self.rule = Rule(id="no-print-statements", description="test")

    def test_fixes_simple_print(self):
        result = self.fixer.fix_line('    print("hello")\n', self.rule)
        assert result == '    logger.info("hello")\n'

    def test_fixes_print_multiple_args(self):
        result = self.fixer.fix_line("    print(x, y, z)\n", self.rule)
        assert result == "    logger.info(x, y, z)\n"

    def test_leaves_logger_line(self):
        result = self.fixer.fix_line('    logger.info("hello")\n', self.rule)
        assert result is None


class TestFixerRegistry:
    def test_get_fixer_known(self):
        fixer = get_fixer("bp-explicit-exceptions")
        assert fixer is not None
        assert isinstance(fixer, BareExceptFixer)

    def test_get_fixer_unknown(self):
        assert get_fixer("nonexistent-rule") is None

    def test_list_fixable_ids(self):
        ids = list_fixable_rule_ids()
        assert "bp-explicit-exceptions" in ids
        assert "no-print-statements" in ids

    def test_register_custom(self):
        class DummyFixer(BareExceptFixer):
            @property
            def rule_id(self):
                return "test-dummy"

        register(DummyFixer())
        assert get_fixer("test-dummy") is not None


class TestApplyFixes:
    def test_file_not_found(self, tmp_path):
        violations = [
            ArchitecturalViolation(
                file=str(tmp_path / "nonexistent.py"),
                line=1,
                rule_id="bp-explicit-exceptions",
                description="test",
            )
        ]
        BP_ID = "bp-explicit-exceptions"
        rules_map = {BP_ID: Rule(id=BP_ID, description="test")}
        results = apply_fixes(violations, rules_map, dry_run=True)
        assert len(results) == 1
        assert not results[0].fixed

    def test_dry_run_does_not_modify(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("except:\n")
        violations = [
            ArchitecturalViolation(
                file=str(f), line=1,
                rule_id="bp-explicit-exceptions",
                description="bare except",
            )
        ]
        BP_ID = "bp-explicit-exceptions"
        rules_map = {BP_ID: Rule(id=BP_ID, description="test")}
        results = apply_fixes(violations, rules_map, dry_run=True)
        assert len(results) == 1
        assert results[0].fixed
        assert f.read_text() == "except:\n"  # unchanged

    def test_apply_fix_modifies_file(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("except:\n")
        violations = [
            ArchitecturalViolation(
                file=str(f), line=1,
                rule_id="bp-explicit-exceptions",
                description="bare except",
            )
        ]
        BP_ID = "bp-explicit-exceptions"
        rules_map = {BP_ID: Rule(id=BP_ID, description="test")}
        results = apply_fixes(violations, rules_map, dry_run=False)
        assert len(results) == 1
        assert results[0].fixed
        assert f.read_text() == "except Exception:\n"

    def test_multiline_fix(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("def foo():\n    except:\n    pass\n")
        violations = [
            ArchitecturalViolation(
                file=str(f), line=2,
                rule_id="bp-explicit-exceptions",
                description="bare except",
            )
        ]
        BP_ID = "bp-explicit-exceptions"
        rules_map = {BP_ID: Rule(id=BP_ID, description="test")}
        results = apply_fixes(violations, rules_map, dry_run=False)
        assert len(results) == 1
        assert results[0].fixed
        assert f.read_text() == "def foo():\n    except Exception:\n    pass\n"

    def test_skip_unknown_rule(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("except:\n")
        violations = [
            ArchitecturalViolation(
                file=str(f), line=1, rule_id="unknown-rule", description="test"
            )
        ]
        rules_map = {}
        results = apply_fixes(violations, rules_map)
        assert len(results) == 0  # no fixer for unknown rule
