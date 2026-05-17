from unittest.mock import MagicMock

import pytest

from aegis.kernel.server import AegisKernel


@pytest.fixture
def kernel():
    k = AegisKernel()
    mock_container = MagicMock()
    mock_container.workspace_root = "/fake/project"
    mock_container.policy_parser.parse_rules.return_value = []
    k.container = mock_container
    return k


class TestMCPPrompts:
    """Test suite for MCP Prompt endpoints."""

    @pytest.mark.asyncio
    async def test_all_governance_prompts_registered(self, kernel):
        prompts = await kernel.mcp.list_prompts()
        names = [p.name for p in prompts]
        assert "evaluate-architecture" in names
        assert "remediate-violations" in names
        assert "explain-rule" in names
        assert "inspect-dependency" in names

    @pytest.mark.asyncio
    async def test_prompts_have_description(self, kernel):
        prompts = await kernel.mcp.list_prompts()
        for p in prompts:
            if p.name.startswith(("evaluate", "remediate", "explain", "inspect")):
                assert p.description, f"Prompt {p.name} missing description"

    @pytest.mark.asyncio
    async def test_evaluate_prompt_content(self, kernel):
        result = await kernel.mcp.get_prompt("evaluate-architecture")
        assert result is not None
        assert "validate_architecture_compliance" in str(result)

    @pytest.mark.asyncio
    async def test_remediate_prompt_content(self, kernel):
        result = await kernel.mcp.get_prompt("remediate-violations")
        assert result is not None
        assert "apply_architectural_remediation" in str(result)

    @pytest.mark.asyncio
    async def test_explain_rule_prompt_accepts_arguments(self, kernel):
        result = await kernel.mcp.get_prompt(
            "explain-rule", arguments={"rule_id": "r1"}
        )
        assert result is not None
        assert "r1" in str(result)
        assert "get_rule_rationale" in str(result)

    @pytest.mark.asyncio
    async def test_inspect_dependency_prompt_accepts_arguments(self, kernel):
        result = await kernel.mcp.get_prompt(
            "inspect-dependency", arguments={"node_name": "src.main"}
        )
        assert result is not None
        assert "src.main" in str(result)
        assert "get_dependency_graph" in str(result)
