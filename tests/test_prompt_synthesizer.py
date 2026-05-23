from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.evaluation.prompt_synthesizer import RemediationPromptSynthesizer
from aegis.domain.policy.models import EnforcementMode, Rule, RuleCategory, Severity


class TestRemediationPromptSynthesizer:
    """
    Test suite for the RemediationPromptSynthesizer.
    """

    def _make_violation(
        self, file, line, rule_id, desc, severity="HIGH", signature=None
    ):
        return ArchitecturalViolation(
            file=file,
            line=line,
            rule_id=rule_id,
            description=desc,
            severity=severity,
            signature=signature,
        )

    def test_empty_violations_returns_ok(self):
        synth = RemediationPromptSynthesizer()
        result = synth.generate_remediation([], {})
        assert "No remediation required" in result.summary

    def test_single_violation_includes_details(self):
        synth = RemediationPromptSynthesizer()
        rule = Rule(
            id="no-test",
            description="No loose functions.",
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
        )
        violations = [
            self._make_violation("src/main.py", 5, "no-test", "Loose function")
        ]
        result = synth.generate_remediation(violations, {"no-test": rule})
        assert "src/main.py" in result.handoff_prompt
        assert "Line 5" in result.handoff_prompt
        assert "no-test" in result.handoff_prompt
        assert "Loose function" in result.handoff_prompt
        assert "block" in result.handoff_prompt
        assert "Execution Directive" in result.handoff_prompt

    def test_multiple_violations_all_listed(self):
        synth = RemediationPromptSynthesizer()
        rules_map = {
            "r1": Rule(
                id="r1",
                description="Rule 1",
                severity=Severity.HIGH,
                mode=EnforcementMode.BLOCK,
            ),
            "r2": Rule(
                id="r2",
                description="Rule 2",
                severity=Severity.MEDIUM,
                mode=EnforcementMode.WARN,
            ),
        }
        violations = [
            self._make_violation("a.py", 1, "r1", "Violation 1"),
            self._make_violation("b.py", 10, "r2", "Violation 2"),
        ]
        result = synth.generate_remediation(violations, rules_map)
        assert violations[0].file in result.handoff_prompt
        assert violations[1].file in result.handoff_prompt
        assert "Violation 1" in result.handoff_prompt
        assert "Violation 2" in result.handoff_prompt
        assert "warn" in result.handoff_prompt
        assert "block" in result.handoff_prompt

    def test_rationale_included_when_present(self):
        synth = RemediationPromptSynthesizer()
        rule = Rule(
            id="r1",
            description="No infra in domain",
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
            rationale="Hexagonal architecture mandates domain isolation.",
        )
        violations = [self._make_violation("domain/main.py", 3, "r1", "Infra import")]
        result = synth.generate_remediation(violations, {"r1": rule})
        assert "Hexagonal architecture" in result.handoff_prompt
        assert "Architectural Rationale" in result.handoff_prompt

    def test_code_context_included_for_existing_file(self, tmp_path):
        """Violations with valid files get code context in remediation."""
        synth = RemediationPromptSynthesizer()
        f = tmp_path / "main.py"
        f.write_text("line1\nline2\nline3\nline4\nline5\n", encoding="utf-8")
        rule = Rule(
            id="r1",
            description="test",
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
        )
        violations = [self._make_violation(str(f), 3, "r1", "Bad code")]
        result = synth.generate_remediation(violations, {"r1": rule})
        assert "Code Context" in result.handoff_prompt
        assert "line3" in result.handoff_prompt

    def test_code_context_omitted_for_missing_file(self):
        """Violations with non-existent files get no code context."""
        synth = RemediationPromptSynthesizer()
        rule = Rule(
            id="r1",
            description="test",
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
        )
        violations = [self._make_violation("/nonexistent/path.py", 3, "r1", "Bad")]
        result = synth.generate_remediation(violations, {"r1": rule})
        assert "Code Context" not in result.handoff_prompt

    def test_fetch_code_context_file_not_found(self, tmp_path):
        """_fetch_code_context returns empty string for missing file."""
        synth = RemediationPromptSynthesizer()
        result = synth._fetch_code_context(
            str(tmp_path / "missing.py"),
            1,
        )
        assert result == ""

    def test_fetch_code_context_normal_file(self, tmp_path):
        """_fetch_code_context returns formatted lines around the violation line."""
        f = tmp_path / "test.py"
        f.write_text(
            "line1\nline2\nline3\nline4\nline5\nline6\nline7\n",
            encoding="utf-8",
        )
        synth = RemediationPromptSynthesizer()
        result = synth._fetch_code_context(str(f), 4)
        # Line 4 should be marked with >
        assert ">    4 | line4" in result

    def test_fetch_code_context_first_line(self, tmp_path):
        """_fetch_code_context handles violation on line 1 without negative indexing."""
        f = tmp_path / "test.py"
        f.write_text("first\nsecond\nthird\nfourth\nfifth\n", encoding="utf-8")
        synth = RemediationPromptSynthesizer()
        result = synth._fetch_code_context(str(f), 1)
        assert ">    1 | first" in result

    def test_fetch_code_context_last_line(self, tmp_path):
        """_fetch_code_context handles violation on last line without exceeding."""
        f = tmp_path / "test.py"
        f.write_text("line1\nline2\nline3\n", encoding="utf-8")
        synth = RemediationPromptSynthesizer()
        result = synth._fetch_code_context(str(f), 3)
        assert ">    3 | line3" in result

    def test_code_context_integration_with_remediation(self, tmp_path):
        """Remediation prompt includes code context for real files."""
        synth = RemediationPromptSynthesizer()
        f = tmp_path / "service.py"
        f.write_text(
            "import os\nimport sys\n\ndef bad():\n    print('evil')\n",
            encoding="utf-8",
        )
        rule = Rule(
            id="no-print",
            description="No prints",
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
        )
        violations = [self._make_violation(str(f), 4, "no-print", "Used print")]
        result = synth.generate_remediation(violations, {"no-print": rule})
        assert "Code Context" in result.handoff_prompt
        assert "print('evil')" in result.handoff_prompt
        assert "Execution Directive" in result.handoff_prompt

    def test_rationale_omitted_when_missing(self):
        synth = RemediationPromptSynthesizer()
        rule = Rule(
            id="r1",
            description="No infra in domain",
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
        )
        violations = [self._make_violation("domain/main.py", 3, "r1", "Infra import")]
        result = synth.generate_remediation(violations, {"r1": rule})
        assert "Architectural Rationale" not in result.handoff_prompt

    def test_security_violation_gets_critical_tag(self):
        synth = RemediationPromptSynthesizer()
        rule = Rule(
            id="sec-1",
            description="No hardcoded secrets",
            severity=Severity.CRITICAL,
            mode=EnforcementMode.BLOCK,
            category=RuleCategory.SECURITY,
        )
        violations = [
            self._make_violation("config.py", 5, "sec-1", "Hardcoded AWS key")
        ]
        result = synth.generate_remediation(violations, {"sec-1": rule})
        assert "CRITICAL SECURITY VULNERABILITY" in result.handoff_prompt
        assert "secure coding practices" in result.handoff_prompt

    def test_architecture_violation_no_security_tag(self):
        synth = RemediationPromptSynthesizer()
        rule = Rule(
            id="arch-1",
            description="Layer isolation",
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
            category=RuleCategory.ARCHITECTURE,
        )
        violations = [
            self._make_violation("domain/main.py", 10, "arch-1", "Infra import")
        ]
        result = synth.generate_remediation(violations, {"arch-1": rule})
        assert "CRITICAL SECURITY VULNERABILITY" not in result.handoff_prompt
        assert "Violation in" in result.handoff_prompt

    def test_mixed_security_and_architecture_violations(self):
        synth = RemediationPromptSynthesizer()
        rules_map = {
            "sec-1": Rule(
                id="sec-1",
                description="Secret check",
                severity=Severity.CRITICAL,
                mode=EnforcementMode.BLOCK,
                category=RuleCategory.SECURITY,
            ),
            "arch-1": Rule(
                id="arch-1",
                description="Layer isolation",
                severity=Severity.HIGH,
                mode=EnforcementMode.BLOCK,
                category=RuleCategory.ARCHITECTURE,
            ),
        }
        violations = [
            self._make_violation("config.py", 5, "sec-1", "Hardcoded key"),
            self._make_violation("domain/main.py", 10, "arch-1", "Infra import"),
        ]
        result = synth.generate_remediation(violations, rules_map)
        assert "CRITICAL SECURITY VULNERABILITY" in result.handoff_prompt
        assert "Violation in" in result.handoff_prompt
        # Security violation should appear first
        assert result.handoff_prompt.index(
            "CRITICAL SECURITY"
        ) < result.handoff_prompt.rindex("Violation in")
