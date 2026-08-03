"""
Unit tests for Aegis Native Runtime nodes and executor.
"""

import pytest

from aegis.domain.evaluation.analyzers.ast import TreeSitterAnalyzer
from aegis.domain.evaluation.analyzers.graph import GraphAnalyzer
from aegis.domain.evaluation.analyzers.regex import RegexAnalyzer
from aegis.domain.evaluation.service import EvaluationService
from aegis.domain.policy.models import EngineType, Rule, Severity
from aegis.runtime.executor import AegisGovernanceError, NativeAegisExecutor
from aegis.runtime.nodes import AegisEnforcementNode, AegisPlanVerifier
from aegis.runtime.wrappers import aegis_hardened_tool


@pytest.fixture
def sample_rules():
    rule1 = Rule(
        id="RULE-DISALLOWED-IMPORT",
        description="Domain modules must not import Infrastructure",
        severity=Severity.HIGH,
        engine_type=EngineType.GRAPH,
        query="disallowed_import",
        metadata={"source": "domain", "target": "infrastructure"},
    )
    rule2 = Rule(
        id="RULE-NO-PRINT",
        description="Print statements forbidden",
        severity=Severity.HIGH,
        engine_type=EngineType.REGEX,
        query=r"print\(",
        language="python",
    )
    return [rule1, rule2]


@pytest.fixture
def eval_service():
    return EvaluationService(
        tree_sitter_analyzer=TreeSitterAnalyzer(),
        graph_analyzer=GraphAnalyzer(),
        regex_analyzer=RegexAnalyzer(),
    )


def test_plan_verifier_rejection(sample_rules):
    verifier = AegisPlanVerifier(sample_rules)

    # Propose domain importing infrastructure
    res = verifier.verify_plan(
        proposed_imports=["aegis.infrastructure.installer"],
        target_module="aegis.domain.evaluation",
    )
    assert res["plan_valid"] is False
    assert len(res["violations"]) == 1
    assert "PLAN REJECTED" in res["feedback"]

    # Compliant plan
    res_clean = verifier.verify_plan(
        proposed_imports=["aegis.domain.policy"],
        target_module="aegis.domain.evaluation",
    )
    assert res_clean["plan_valid"] is True


def test_enforcement_node_evaluate_delta(eval_service, sample_rules):
    node = AegisEnforcementNode(eval_service, sample_rules)

    res_clean = node.evaluate_delta("def foo(): pass", "python")
    assert res_clean["governance_valid"] is True

    res_dirty = node.evaluate_delta("print('hello')", "python")
    assert res_dirty["governance_valid"] is False
    assert res_dirty["total_violations"] == 1
    assert res_dirty["remediation_prompt"] is not None


def test_native_executor_blocks_violation(eval_service, sample_rules):
    executor = NativeAegisExecutor(eval_service, sample_rules)

    def dummy_tool(content: str):
        return f"Wrote: {content}"

    # Clean call
    out = executor.execute_tool("write_file", {"content": "x = 1"}, dummy_tool)
    assert out == "Wrote: x = 1"

    # Dirty call raising governance error
    with pytest.raises(AegisGovernanceError) as exc_info:
        executor.execute_tool("write_file", {"content": "print('bad')"}, dummy_tool)

    assert "Tool 'write_file' blocked" in str(exc_info.value)
    assert len(exc_info.value.violations) == 1


def test_hardened_tool_decorator(eval_service, sample_rules):
    @aegis_hardened_tool(eval_service, sample_rules)
    def my_tool(content: str):
        return "success"

    assert my_tool(content="a = 42") == "success"

    with pytest.raises(AegisGovernanceError):
        my_tool(content="print('fail')")


def test_enforcement_node_call_interface(eval_service, sample_rules):
    node = AegisEnforcementNode(eval_service, sample_rules)

    state = {
        "pending_tool_call": {"path": "test.py", "content": "print('bad')"},
    }
    update = node(state)
    assert update["governance_valid"] is False
    assert len(update["governance"]) == 1
    assert update["governance"][0]["is_clean"] is False


def test_circuit_breaker_trigger(eval_service, sample_rules, tmp_path):
    from aegis.core.baseline import BaselineManager

    bm = BaselineManager(directory=str(tmp_path))
    node = AegisEnforcementNode(eval_service, sample_rules, baseline_manager=bm)

    state = {
        "pending_tool_call": {"path": "test.py", "content": "print('bad')"},
        "governance_retry_count": 2,
        "max_governance_retries": 3,
    }

    update = node(state)
    assert update["circuit_broken"] is True
    assert update["governance_valid"] is True  # Circuit breaker unblocks graph loop
    assert update["governance_retry_count"] == 3
    assert "CIRCUIT BREAKER TRIGGERED" in update["governance"][0]["remediation_prompt"]


def test_plan_verifier_string_imports(sample_rules):
    verifier = AegisPlanVerifier(sample_rules)

    # String input with comma/space separated imports (2 infrastructure imports)
    res = verifier.verify_plan(
        proposed_imports="aegis.infrastructure.installer, aegis.infrastructure.harness",
        target_module="aegis.domain.evaluation",
    )
    assert res["plan_valid"] is False
    assert len(res["violations"]) == 2


