"""
Native LangGraph/DeepAgents state graph nodes for Aegis governance.

Implements AegisPlanVerifier (proactive intent check), AegisEnforcementNode (AST delta gatekeeper),
and AegisFinalGate (structural/security invariant validator).
"""

from typing import Any

from aegis.core.baseline import BaselineManager
from aegis.core.registry import Rule, RuleCategory
from aegis.domain.evaluation_service import EvaluationService
from aegis.domain.synthesizer import RemediationPromptSynthesizer


class AegisPlanVerifier:
    """
    Proactive pre-flight plan verifier node.
    Evaluates proposed architectural intent (e.g. imports, tiers, file paths)
    against rules BEFORE code generation starts, saving token costs.
    """

    def __init__(self, rules: list[Rule]):
        self.rules = rules

    def verify_plan(
        self, proposed_imports: list[str], target_module: str
    ) -> dict[str, Any]:
        """
        Verify proposed imports against disallowed_import graph rules.
        """
        violations = []
        for rule in self.rules:
            if rule.query == "disallowed_import":
                source_ns = rule.metadata.get("source") or rule.metadata.get(
                    "source_module", ""
                )
                target_ns = rule.metadata.get("target") or rule.metadata.get(
                    "target_module", ""
                )

                if source_ns and target_ns and source_ns in target_module.split("."):
                    for imp in proposed_imports:
                        if target_ns in imp.split("."):
                            violations.append(
                                {
                                    "rule_id": rule.id,
                                    "description": f"{rule.description}: {target_module} proposing import of {imp}",
                                    "severity": rule.severity.value,
                                }
                            )

        is_valid = len(violations) == 0
        return {
            "plan_valid": is_valid,
            "violations": violations,
            "feedback": (
                f"PLAN REJECTED: Proactive architectural violations detected: {violations}"
                if not is_valid
                else "PLAN APPROVED"
            ),
        }


class AegisEnforcementNode:
    """
    In-process AST delta gatekeeper node for StateGraph execution loops.
    Evaluates pending code modifications against rules in-memory.
    """

    def __init__(
        self,
        evaluation_service: EvaluationService,
        rules: list[Rule],
        baseline_manager: BaselineManager | None = None,
    ):
        self.evaluation = evaluation_service
        self.rules = rules
        self.baseline = baseline_manager
        self.prompt_synthesizer = RemediationPromptSynthesizer()

    def evaluate_delta(
        self,
        code_string: str,
        language: str = "python",
        file_path: str | None = None,
        rules: list[Rule] | None = None,
    ) -> dict[str, Any]:
        """
        Evaluates a proposed code payload in memory against active rules.
        """
        active_rules = rules if rules is not None else self.rules
        violations = self.evaluation.evaluate_code_string(
            code_string, language, active_rules
        )

        active_violations = []
        for v in violations:
            rule = next((r for r in active_rules if r.id == v.rule_id), None)
            if self.baseline and self.baseline.is_exempt(v, rule):
                continue
            active_violations.append(v)

        is_clean = len(active_violations) == 0
        remediation_prompt = None
        if not is_clean:
            remediation_prompt = self.prompt_synthesizer.synthesize(
                active_violations, active_rules
            )

        return {
            "governance_valid": is_clean,
            "total_violations": len(violations),
            "active_violations": [v.model_dump() for v in active_violations],
            "remediation_prompt": remediation_prompt,
        }

    def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        LangGraph StateGraph node execution entry point.
        Extracts pending_tool_call from state, evaluates in-memory AST delta,
        and returns governance state update.
        """
        pending = state.get("pending_tool_call") or {}
        code_string = pending.get("content") or pending.get("code") or ""
        file_path = pending.get("path") or pending.get("file_path")
        language = "python"
        if file_path and file_path.endswith((".ts", ".js")):
            language = "typescript" if file_path.endswith(".ts") else "javascript"

        res = self.evaluate_delta(
            code_string=code_string, language=language, file_path=file_path
        )
        ctx = {
            "is_clean": res["governance_valid"],
            "total_violations": res["total_violations"],
            "active_violations": res["active_violations"],
            "remediation_prompt": res["remediation_prompt"],
        }
        return {
            "governance_valid": res["governance_valid"],
            "governance": [ctx],
        }


class AegisFinalGate:
    """
    Final structural validator node enforcing zero-tolerance security rules.
    """

    def __init__(self, rules: list[Rule]):
        self.security_rules = [r for r in rules if r.category == RuleCategory.SECURITY]

    def validate_security(self, active_violations: list[dict]) -> bool:
        """Return False if any active violation belongs to a SECURITY category rule."""
        sec_ids = {r.id for r in self.security_rules}
        for v in active_violations:
            if v.get("rule_id") in sec_ids:
                return False
        return True
