"""
Multi-Scenario Efficiency Benchmark Test Suite for Aegis Native Governance Engine.

Measures token efficiency and latency across 5 architectural scenarios.
"""

import time

import pytest

from aegis.adapters.deepagents import create_deepagents_governed_agent
from aegis.adapters.langgraph import LangGraphAdapter
from aegis.core import Rule, RuleCategory, Severity
from aegis.domain.evaluation.analyzers.ast import TreeSitterAnalyzer
from aegis.domain.evaluation.analyzers.graph import GraphAnalyzer
from aegis.domain.evaluation.analyzers.regex import RegexAnalyzer
from aegis.domain.evaluation.service import EvaluationService
from aegis.runtime.executor import AegisGovernanceError, NativeAegisExecutor
from aegis.runtime.nodes import AegisEnforcementNode, AegisPlanVerifier


@pytest.fixture
def benchmark_rules():
    rule1 = Rule(
        id="arch-layer-domain-iso",
        description="Domain modules must not import infrastructure layer modules",
        severity=Severity.HIGH,
        category=RuleCategory.ARCHITECTURE,
        engine_type="graph",
        query="disallowed_import",
        metadata={"source": "domain", "target": "infrastructure"},
    )
    rule2 = Rule(
        id="no-print-in-prod",
        description="Print statements are strictly forbidden in production code",
        severity=Severity.HIGH,
        category=RuleCategory.STYLE,
        engine_type="regex",
        query=r"print\(",
        language="python",
    )
    rule3 = Rule(
        id="no-raw-exec",
        description="Raw exec statements forbidden for security",
        severity=Severity.HIGH,
        category=RuleCategory.SECURITY,
        engine_type="regex",
        query=r"exec\(",
        language="python",
    )
    return [rule1, rule2, rule3]


def test_scenario_1_pre_flight_plan_gate_token_interception(benchmark_rules):
    """
    Scenario 1: Pre-Flight Intent Verification Interception
    Proves that AegisPlanVerifier halts non-compliant intent before LLM generates code.
    """
    verifier = AegisPlanVerifier(benchmark_rules)

    start_ns = time.perf_counter_ns()
    res = verifier.verify_plan(
        proposed_imports=["infrastructure.database.orm"],
        target_module="domain.user_aggregate",
    )
    elapsed_us = (time.perf_counter_ns() - start_ns) / 1000.0

    assert res["plan_valid"] is False
    assert len(res["violations"]) == 1
    assert res["violations"][0]["rule_id"] == "arch-layer-domain-iso"
    assert "PLAN REJECTED" in res["feedback"]
    assert elapsed_us < 5000.0


def test_scenario_2_in_memory_ast_delta_eval_latency(benchmark_rules):
    """
    Scenario 2: In-Memory AST Delta Compiler Speed & Accuracy
    Proves Tree-sitter AST and Regex analysis executes in microseconds without disk I/O.
    """
    eval_service = EvaluationService(
        tree_sitter_analyzer=TreeSitterAnalyzer(),
        graph_analyzer=GraphAnalyzer(),
        regex_analyzer=RegexAnalyzer(),
    )
    node = AegisEnforcementNode(eval_service, benchmark_rules)

    bad_code = "def process_data(payload):\n    print(f'Payload: {payload}')\n    exec(payload)\n"

    start_ns = time.perf_counter_ns()
    res = node.evaluate_delta(bad_code, "python", "src/domain/service.py")
    elapsed_us = (time.perf_counter_ns() - start_ns) / 1000.0

    assert res["governance_valid"] is False
    assert res["total_violations"] == 2
    assert res["remediation_prompt"] is not None
    assert elapsed_us < 10000.0


def test_scenario_3_sealed_tool_executor_disk_integrity(benchmark_rules):
    """
    Scenario 3: Sealed Tool Executor Disk Integrity Interception
    Proves NativeAegisExecutor intercepts dirty tool calls and raises AegisGovernanceError.
    """
    eval_service = EvaluationService(
        tree_sitter_analyzer=TreeSitterAnalyzer(),
        graph_analyzer=GraphAnalyzer(),
        regex_analyzer=RegexAnalyzer(),
    )
    executor = NativeAegisExecutor(eval_service, benchmark_rules)

    written_files = {}

    def mock_write(path: str, content: str):
        written_files[path] = content
        return "SUCCESS"

    with pytest.raises(AegisGovernanceError) as exc_info:
        executor.execute_tool(
            "write_file",
            {"path": "src/domain/payment.py", "content": "print('dirty write')"},
            mock_write,
        )

    assert "Tool 'write_file' blocked" in str(exc_info.value)
    assert "src/domain/payment.py" not in written_files

    res = executor.execute_tool(
        "write_file",
        {"path": "src/domain/payment.py", "content": "x = 100"},
        mock_write,
    )
    assert res == "SUCCESS"
    assert written_files["src/domain/payment.py"] == "x = 100"


def test_scenario_4_deepagents_self_correction_refinement_loop(benchmark_rules, tmp_path):
    """
    Scenario 4: Multi-Turn Self-Correction Refinement Loop (DeepAgentsAdapter)
    """
    workspace = str(tmp_path)
    agent = create_deepagents_governed_agent(workspace_root=workspace, rules=benchmark_rules)

    attempts_log = []

    def mock_deepagents_generator(prompt: str):
        attempts_log.append(prompt)
        if len(attempts_log) == 1:
            return {"path": "src/domain/checkout.py", "code": "print('checkout')"}
        else:
            return {"path": "src/domain/checkout.py", "code": "def checkout(): pass"}

    written_files = {}

    def mock_write(path: str, content: str):
        written_files[path] = content
        return "WRITTEN"

    res = agent.run_governed_agent_loop(
        initial_request="Implement checkout module",
        code_generator_fn=mock_deepagents_generator,
        tool_fn=mock_write,
        max_retries=3,
    )

    assert res["success"] is True
    assert res["attempts"] == 2
    assert written_files["src/domain/checkout.py"] == "def checkout(): pass"


def test_scenario_5_langgraph_stategraph_node_execution(benchmark_rules):
    """
    Scenario 5: Native LangGraph StateGraph Node Execution
    """
    adapter = LangGraphAdapter(rules=benchmark_rules, workspace_root=".")

    state = {
        "pending_tool_call": {
            "name": "write_file",
            "path": "src/domain/order.py",
            "content": "class Order:\n    pass\n",
        }
    }

    res_state = adapter.run_step(state)
    assert res_state["governance_valid"] is True
