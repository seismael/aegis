import os

import pytest

from aegis.kernel.server import AegisKernel


@pytest.fixture
def workspace_root(tmp_path):
    # Create a temp dir using pytest's tmp_path fixture
    tmp_dir = str(tmp_path)
    return tmp_dir


@pytest.mark.asyncio
async def test_agent_coordination_persistence(workspace_root):
    workspace = workspace_root
    os.makedirs(os.path.join(workspace, ".aegis", "rules"), exist_ok=True)

    # Create a dummy rule pack so _load_rules returns something
    with open(os.path.join(workspace, ".aegis", "rules", "custom.yaml"), "w") as f:
        f.write(
            "rules:\n  - id: dummy\n    description: dummy\n    engine_type: regex\n    category: architecture\n    mode: block\n    query: dummy\n"
        )

    # Initialize kernel with temp workspace
    kernel = AegisKernel(workspace_root=workspace)

    # Simulate Agent 1
    os.environ["AEGIS_AGENT_ID"] = "Agent-1"
    note = "Refactoring complete, please verify architectural compliance."

    # First validation call
    await kernel.check_architecture(files_modified=["src/main.py"], handoff_note=note)

    # Verify session was saved
    session_file = os.path.join(workspace, ".aegis", "session.json")
    assert os.path.exists(session_file)

    state = kernel.session.load()
    assert state.last_agent_id == "Agent-1"
    assert state.handoff_notes == note
    assert state.last_validation_time is not None

    # Simulate Agent 2
    os.environ["AEGIS_AGENT_ID"] = "Agent-2"

    # Second validation call - should show coordination info
    result = await kernel.check_architecture(files_modified=["src/main.py"])

    assert "### 🤝 Coordination Info" in result
    assert "Last validated by: **Agent-1**" in result
    assert f"Handoff Notes: {note}" in result

    # Verify Agent 2 updated the state
    state2 = kernel.session.load()
    assert state2.last_agent_id == "Agent-2"

    # Clean up env
    if "AEGIS_AGENT_ID" in os.environ:
        del os.environ["AEGIS_AGENT_ID"]


@pytest.mark.asyncio
async def test_agent_coordination_same_agent_no_info(workspace_root):
    workspace = workspace_root
    os.makedirs(os.path.join(workspace, ".aegis", "rules"), exist_ok=True)

    # Create a dummy rule pack so _load_rules returns something
    with open(os.path.join(workspace, ".aegis", "rules", "custom.yaml"), "w") as f:
        f.write(
            "rules:\n  - id: dummy\n    description: dummy\n    engine_type: regex\n    category: architecture\n    mode: block\n    query: dummy\n"
        )

    kernel = AegisKernel(workspace_root=workspace)

    os.environ["AEGIS_AGENT_ID"] = "Agent-SAME"

    # First call
    await kernel.check_architecture(files_modified=["src/main.py"])

    # Second call by same agent, no handoff note - should NOT show info
    result = await kernel.check_architecture(files_modified=["src/main.py"])

    assert "### 🤝 Coordination Info" not in result

    # Third call with handoff note
    await kernel.check_architecture(
        files_modified=["src/main.py"], handoff_note="New note"
    )

    # Fourth call by same agent - should show info because handoff note exists
    result = await kernel.check_architecture(files_modified=["src/main.py"])
    assert "### 🤝 Coordination Info" in result
    assert "Handoff Notes: New note" in result

    # Clean up env
    if "AEGIS_AGENT_ID" in os.environ:
        del os.environ["AEGIS_AGENT_ID"]
