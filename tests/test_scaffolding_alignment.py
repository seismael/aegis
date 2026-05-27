import pytest

from aegis.kernel.server import AegisKernel


@pytest.mark.asyncio
async def test_scaffold_governance_framework_generates_all_instruction_files(tmp_path):
    """
    Test Task 3: Align Scaffolding with Universal Harnesses
    Verifies that scaffold_governance_framework generates AGENTS.md, .claude.md, and GEMINI.md.
    """
    ws = tmp_path / "scaffold-alignment-test"
    ws.mkdir()
    (ws / "pyproject.toml").write_text('[project]\nname = "test"\n')

    # Initialize kernel with temporary workspace
    kernel = AegisKernel(str(ws))

    # Call scaffold_governance_framework
    # We pass an empty list or some packs; it should still deploy instructions.
    result = await kernel.scaffold_governance_framework(["best-practices"])

    assert "SUCCESS" in result
    assert "AGENTS.md" in result
    assert ".claude.md" in result
    assert "GEMINI.md" in result

    # Check for all three instruction files
    assert (ws / "AGENTS.md").exists(), "AGENTS.md missing"
    assert (ws / ".claude.md").exists(), ".claude.md missing"
    assert (ws / "GEMINI.md").exists(), "GEMINI.md missing"

    # Verify some content to ensure they are the right files
    assert "Aegis" in (ws / "AGENTS.md").read_text()
    assert "Claude" in (ws / ".claude.md").read_text()
    assert "Gemini" in (ws / "GEMINI.md").read_text()
