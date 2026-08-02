"""
Unit tests for AegisAgent factory.
"""

from aegis.agent import AegisAgent, create_aegis_agent
from aegis.domain.policy.models import EngineType, Rule, Severity


def test_aegis_agent_factory():
    rule = Rule(
        id="RULE-TEST",
        description="No print statements",
        severity=Severity.HIGH,
        engine_type=EngineType.REGEX,
        query=r"print\(",
        language="python",
    )

    agent = create_aegis_agent(rules=[rule], workspace_root=".")
    assert isinstance(agent, AegisAgent)

    plan_res = agent.verify_plan(
        proposed_imports=["aegis.domain"], target_module="aegis.kernel"
    )
    assert plan_res["plan_valid"] is True

    delta_clean = agent.evaluate_code_delta("v = 10", "python")
    assert delta_clean["governance_valid"] is True

    delta_dirty = agent.evaluate_code_delta("print(10)", "python")
    assert delta_dirty["governance_valid"] is False
