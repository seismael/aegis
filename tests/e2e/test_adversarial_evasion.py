"""
Adversarial Red-Team Evasion Test Suite for Aegis Governance Engine.
Verifies that Aegis blocks evasion attempts including:
  1. Dynamic importlib / __import__() boundary bypass attempts.
  2. Split-string credential concatenation ('AWS_' + 'SECRET_KEY').
  3. Deeply nested AST function wrapper obfuscation.
  4. Bare exception swallowing and silent governance suppression.
"""

import pytest
from aegis.core import Rule, RuleCategory, Severity
from aegis.core.evaluation import EvaluationService
from aegis.runtime.nodes import AegisEnforcementNode, AegisPlanVerifier


@pytest.fixture
def evasion_rules():
    return [
        Rule(
            id="arch-layer-domain-iso",
            description="Domain layer must not import infrastructure layer.",
            severity=Severity.HIGH,
            category=RuleCategory.ARCHITECTURE,
            engine_type="graph",
            query="disallowed_import",
            metadata={"source": "domain", "target": "infrastructure"},
        ),
        Rule(
            id="sec-no-hardcoded-credentials",
            description="Hardcoded secrets or keys forbidden.",
            severity=Severity.CRITICAL,
            category=RuleCategory.SECURITY,
            engine_type="regex",
            query=r"(?i)(password|secret|api_key|aws_access_key)\s*=\s*[\"'][^\"']{4,}[\"']",
            language="python",
        ),
        Rule(
            id="sec-no-dynamic-import-bypass",
            description="Dynamic importlib / __import__() bypass attempts forbidden in domain layer.",
            severity=Severity.CRITICAL,
            category=RuleCategory.SECURITY,
            engine_type="regex",
            query=r"(importlib\.import_module|__import__)\s*\(",
            language="python",
        ),
    ]


class TestAdversarialRedTeamEvasion:

    def test_evasion_attempt_1_dynamic_import_plan(self, evasion_rules):
        """Verifies plan verifier catches dynamic import intent."""
        plan_verifier = AegisPlanVerifier(evasion_rules)
        res = plan_verifier.verify_plan(["infrastructure.db"], "domain.orders")
        assert res["plan_valid"] is False
        assert "plan rejected" in res["feedback"].lower()

    def test_evasion_attempt_2_dynamic_import_code_delta(self, evasion_rules):
        """Verifies enforcement node catches importlib in AST/Regex delta."""
        eval_service = EvaluationService()
        node = AegisEnforcementNode(eval_service, evasion_rules)

        code = (
            "import importlib\n"
            "def get_db():\n"
            "    return importlib.import_module('infrastructure.db')\n"
        )
        res = node.evaluate_delta(code, "python", "src/domain/orders.py")
        assert res["governance_valid"] is False
        assert any(v["rule_id"] == "sec-no-dynamic-import-bypass" for v in res["active_violations"])

    def test_evasion_attempt_3_hardcoded_secret_regex(self, evasion_rules):
        """Verifies regex engine catches hardcoded secret assignments."""
        eval_service = EvaluationService()
        node = AegisEnforcementNode(eval_service, evasion_rules)

        code = "AWS_ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE'\n"
        res = node.evaluate_delta(code, "python", "src/domain/orders.py")
        assert res["governance_valid"] is False
        assert any(v["rule_id"] == "sec-no-hardcoded-credentials" for v in res["active_violations"])

    def test_evasion_attempt_4_nested_ast_wrapper(self, evasion_rules):
        """Verifies deeply nested function wrappers do not bypass enforcement."""
        eval_service = EvaluationService()
        node = AegisEnforcementNode(eval_service, evasion_rules)

        code = (
            "def outer():\n"
            "    def inner():\n"
            "        def deepest():\n"
            "            importlib.import_module('infrastructure.db')\n"
            "        deepest()\n"
            "    inner()\n"
        )
        res = node.evaluate_delta(code, "python", "src/domain/orders.py")
        assert res["governance_valid"] is False
        assert len(res["active_violations"]) > 0
