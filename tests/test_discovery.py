import pytest

from aegis.kernel.models import DiscoveryResult
from aegis.kernel.server import AegisKernel


@pytest.mark.asyncio
async def test_discover_architectural_patterns_structured(tmp_path):
    # Setup a dummy pyproject.toml to trigger Python detection
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")

    kernel = AegisKernel(workspace_root=str(tmp_path))
    result = await kernel.discover_architectural_patterns()

    assert isinstance(result, DiscoveryResult)
    assert len(result.proposals) > 0

    # Check for mandatory security proposal
    security_proposal = next((p for p in result.proposals if p.id == "security"), None)
    assert security_proposal is not None
    assert security_proposal.relevance == 1.0
    assert "Security" in security_proposal.reason
    assert (
        security_proposal.suggested_action == "apply_governance_law(law_id='security')"
    )

    # Check for architecture proposal
    arch_proposal = next((p for p in result.proposals if p.id == "architecture"), None)
    assert arch_proposal is not None
    assert "Python project" in arch_proposal.reason
    assert (
        arch_proposal.suggested_action == "apply_governance_law(law_id='architecture')"
    )


@pytest.mark.asyncio
async def test_hypothesize_workspace_architecture_still_works(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")
    kernel = AegisKernel(workspace_root=str(tmp_path))

    # This should return a string for backward compatibility with query_knowledge_graph
    result = kernel._hypothesize_workspace_architecture()
    assert isinstance(result, str)
    assert "Proposed: architecture" in result
    assert "Python project" in result
