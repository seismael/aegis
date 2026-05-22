from unittest.mock import MagicMock, patch

import pytest

from aegis.kernel.server import AegisKernel


@pytest.fixture
def kernel():
    """AegisKernel with a mocked container."""
    k = AegisKernel()
    mock_container = MagicMock()
    k.container = mock_container
    return k


class TestMCPPrompts:
    """Test suite for MCP Prompt registration and generation."""

    @pytest.mark.asyncio
    async def test_all_prompts_registered(self, kernel):
        """Verify all essential dev-workflow prompts are registered."""
        prompts = await kernel.mcp.list_prompts()
        names = [p.name for p in prompts]
        assert "start-new-task" in names
        assert "evaluate-architecture" in names
        assert "remediate-violations" in names
        assert "explain-rule" in names
        assert "initialize-governance" in names
        assert "inspect-dependency" in names

    @pytest.mark.asyncio
    async def test_start_task_prompt_content(self, kernel):
        """Verify the start-task prompt contains the correct Meta-Tool references."""
        result = await kernel.mcp.get_prompt("start-new-task", arguments={"description": "test"})
        assert result is not None
        assert "plan_architecture" in str(result)
        assert "aegis://dna" in str(result)

    @pytest.mark.asyncio
    async def test_evaluate_prompt_content(self, kernel):
        result = await kernel.mcp.get_prompt("evaluate-architecture")
        assert result is not None
        assert "validate_workspace" in str(result)
        assert "query_knowledge_graph" in str(result)

    @pytest.mark.asyncio
    async def test_remediate_prompt_content(self, kernel):
        result = await kernel.mcp.get_prompt("remediate-violations")
        assert result is not None
        assert "validate_workspace" in str(result)

    @pytest.mark.asyncio
    async def test_explain_rule_prompt_accepts_arguments(self, kernel):
        result = await kernel.mcp.get_prompt(
            "explain-rule", arguments={"rule_id": "r1"}
        )
        assert result is not None
        assert "r1" in str(result)
        assert "query_knowledge_graph" in str(result)

    @pytest.mark.asyncio
    async def test_initialize_governance_prompt(self, kernel):
        result = await kernel.mcp.get_prompt("initialize-governance")
        assert result is not None
        assert "auto_init" in str(result)

    @pytest.mark.asyncio
    async def test_inspect_dependency_prompt_accepts_arguments(self, kernel):
        result = await kernel.mcp.get_prompt(
            "inspect-dependency", arguments={"node_name": "src.main"}
        )
        assert result is not None
        assert "src.main" in str(result)
        assert "query_knowledge_graph" in str(result)
