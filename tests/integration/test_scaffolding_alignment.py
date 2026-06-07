import pytest

from aegis.kernel.server import AegisKernel


@pytest.mark.asyncio
async def test_init_governance_generates_all_instruction_files(tmp_path):
    """
    Test Task 3: Align Scaffolding with Universal Harnesses
    Verifies that init_governance generates AGENTS.md, .claude.md, and GEMINI.md.
    """
    ws = tmp_path / "scaffold-alignment-test"
    ws.mkdir()
    (ws / "pyproject.toml").write_text('[project]\nname = "test"\n')

    # Initialize kernel with temporary workspace
    kernel = AegisKernel(str(ws))

    # Call init_governance
    # We pass an empty list or some packs; it should still deploy instructions.
    result = await kernel.init_governance(["best-practices"])

    assert "SUCCESS" in result
    assert "AGENTS.md" in result
    assert "CLAUDE.md" in result
    assert "GEMINI.md" in result

    # Check for all three instruction files
    assert (ws / "AGENTS.md").exists(), "AGENTS.md missing"
    assert (ws / "CLAUDE.md").exists(), "CLAUDE.md missing"
    assert (ws / "GEMINI.md").exists(), "GEMINI.md missing"

    # Verify some content to ensure they are the right files
    assert "Aegis Governance Protocol" in (ws / "AGENTS.md").read_text() or "Aegis Governance Protocol" in (ws / "CLAUDE.md").read_text()
    assert "Aegis Governance Protocol" in (ws / "CLAUDE.md").read_text()
    assert "Aegis Governance Protocol" in (ws / "GEMINI.md").read_text()
