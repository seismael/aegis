from aegis.domain.enforcement.remediation import RemediationPromptSynthesizer
from aegis.domain.evaluation.ports import ASTViolation
from aegis.core.models.governance import Rule, Severity, EnforcementMode


class TestRemediationPromptSynthesizer:
    """
    Test suite for the RemediationPromptSynthesizer.
    """

    def _make_violation(
        self, file, line, rule_id, desc, severity="HIGH", signature=None
    ):
        return ASTViolation(
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
        assert "No remediation required" in result

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
        assert "src/main.py" in result
        assert "Line 5" in result
        assert "no-test" in result
        assert "Loose function" in result
        assert "block" in result
        assert "Execution Directive" in result

    def test_multiple_violations_all_listed(self):
        synth = RemediationPromptSynthesizer()
        rules_map = {
            "r1": Rule(id="r1", description="Rule 1", severity=Severity.HIGH, mode=EnforcementMode.BLOCK),
            "r2": Rule(id="r2", description="Rule 2", severity=Severity.MEDIUM, mode=EnforcementMode.WARN),
        }
        violations = [
            self._make_violation("a.py", 1, "r1", "Violation 1"),
            self._make_violation("b.py", 10, "r2", "Violation 2"),
        ]
        result = synth.generate_remediation(violations, rules_map)
        assert violations[0].file in result
        assert violations[1].file in result
        assert "Violation 1" in result
        assert "Violation 2" in result
        assert "warn" in result
        assert "block" in result

    def test_rationale_included_when_present(self):
        synth = RemediationPromptSynthesizer()
        rule = Rule(
            id="r1",
            description="No infra in domain",
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
            rationale="Hexagonal architecture mandates domain isolation.",
        )
        violations = [
            self._make_violation("domain/main.py", 3, "r1", "Infra import")
        ]
        result = synth.generate_remediation(violations, {"r1": rule})
        assert "Hexagonal architecture" in result
        assert "Architectural Rationale" in result

    def test_rationale_omitted_when_missing(self):
        synth = RemediationPromptSynthesizer()
        rule = Rule(
            id="r1",
            description="No infra in domain",
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
        )
        violations = [
            self._make_violation("domain/main.py", 3, "r1", "Infra import")
        ]
        result = synth.generate_remediation(violations, {"r1": rule})
        assert "Architectural Rationale" not in result
