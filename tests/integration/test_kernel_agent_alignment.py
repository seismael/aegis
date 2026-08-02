"""
Integration tests verifying AegisKernel, AegisAgent, AegisPlanVerifier,
AegisEnforcementNode, and NativeAegisExecutor alignment with canonical TEMP.md specification.
"""

import pytest

from aegis.agent import AegisAgent, create_aegis_agent
from aegis.domain.policy.models import EngineType, Rule, Severity
from aegis.kernel.server import AegisKernel
from aegis.runtime.executor import AegisGovernanceError, NativeAegisExecutor
from aegis.runtime.nodes import AegisEnforcementNode, AegisPlanVerifier


@pytest.fixture
def mock_rule():
    return Rule(
        id="test-no-print",
        description="No print statements allowed",
        severity=Severity.HIGH,
        engine_type=EngineType.REGEX,
        query=r"print\(",
        applies_to=["**/*.py"],
        mode="block",
    )


@pytest.fixture
def graph_disallowed_rule():
    return Rule(
        id="no-infrastructure-in-domain",
        description="Domain layer must not depend on infrastructure layer",
        severity=Severity.HIGH,
        engine_type=EngineType.GRAPH,
        query="disallowed_import",
        metadata={
            "source_module": "domain",
            "target_module": "infrastructure",
        },
        applies_to=["**/*.py"],
        mode="block",
    )


def test_aegis_agent_factory_initialization(mock_rule, tmp_path):
    agent = create_aegis_agent(rules=[mock_rule], workspace_root=str(tmp_path))
    assert isinstance(agent, AegisAgent)
    assert isinstance(agent.plan_verifier, AegisPlanVerifier)
    assert isinstance(agent.enforcement_node, AegisEnforcementNode)
    assert isinstance(agent.executor, NativeAegisExecutor)


def test_agent_plan_verifier_integration(graph_disallowed_rule, tmp_path):
    agent = create_aegis_agent(
        rules=[graph_disallowed_rule], workspace_root=str(tmp_path)
    )
    res = agent.verify_plan(
        proposed_imports=["aegis.infrastructure.nodes"],
        target_module="aegis.domain.service",
    )
    assert res["plan_valid"] is False
    assert len(res["violations"]) == 1
    assert res["violations"][0]["rule_id"] == "no-infrastructure-in-domain"


def test_agent_code_delta_evaluation(mock_rule, tmp_path):
    agent = create_aegis_agent(rules=[mock_rule], workspace_root=str(tmp_path))
    clean_res = agent.evaluate_code_delta("x = 10\n", "python")
    assert clean_res["governance_valid"] is True

    dirty_res = agent.evaluate_code_delta("print('hello')\n", "python")
    assert dirty_res["governance_valid"] is False
    assert len(dirty_res["active_violations"]) == 1


def test_hardened_executor_interception(mock_rule, tmp_path):
    agent = create_aegis_agent(rules=[mock_rule], workspace_root=str(tmp_path))

    def mock_tool_fn(path: str, content: str):
        return f"Wrote {path}"

    res = agent.execute_tool(
        "write_file",
        {"path": "test.py", "content": "x = 10\n"},
        mock_tool_fn,
    )
    assert res == "Wrote test.py"

    with pytest.raises(AegisGovernanceError) as exc_info:
        agent.execute_tool(
            "write_file",
            {"path": "test.py", "content": "print('bad')\n"},
            mock_tool_fn,
        )
    assert "Aegis Governance Enforcement" in str(exc_info.value)


@pytest.mark.asyncio
async def test_kernel_plan_architecture_integration(tmp_path):
    ws = tmp_path / "project"
    ws.mkdir()
    (ws / ".aegis").mkdir()
    kernel = AegisKernel(workspace_root=str(ws))

    res = await kernel.plan_architecture(
        intent="Add new feature in src/main.py",
        file_path="src/main.py",
        code_string="print('test')\n",
        language="python",
    )
    assert "Architectural Context" in res
