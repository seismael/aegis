import os
import shutil
import pytest
import tempfile
from datetime import datetime
from aegis.domain.evaluation.session import SessionManager, SessionState

@pytest.fixture
def temp_workspace():
    # Use a directory we likely have access to, within the project root
    base_dir = os.path.join(os.getcwd(), "tests", "tmp_sessions")
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    os.makedirs(base_dir, exist_ok=True)
    yield base_dir
    # Cleanup
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)

def test_session_manager_default_state(temp_workspace):
    manager = SessionManager(temp_workspace)
    state = manager.load()
    
    assert isinstance(state, SessionState)
    assert state.last_validation_time is None
    assert state.last_agent_id is None
    assert state.active_task is None
    assert state.handoff_notes is None

def test_session_manager_save_load(temp_workspace):
    manager = SessionManager(temp_workspace)
    now = datetime.now()
    
    state = SessionState(
        last_validation_time=now,
        last_agent_id="agent-007",
        active_task="task-2",
        handoff_notes="Test handoff notes"
    )
    
    manager.save(state)
    
    # Load back
    loaded_state = manager.load()
    
    # Pydantic datetime serialization might lose some precision depending on format, 
    # but isoformat usually preserves it. 
    # For comparison we can check isoformat or allow slight difference if needed.
    assert loaded_state.last_agent_id == "agent-007"
    assert loaded_state.active_task == "task-2"
    assert loaded_state.handoff_notes == "Test handoff notes"
    assert loaded_state.last_validation_time is not None
    # datetime.now() doesn't include timezone by default, pydantic might add Z or offset if configured.
    # In this simple case they should be very close.
    assert loaded_state.last_validation_time.isoformat() == now.isoformat()

def test_session_manager_corrupted_file(temp_workspace):
    manager = SessionManager(temp_workspace)
    session_file = os.path.join(temp_workspace, ".aegis", "session.json")
    
    os.makedirs(os.path.dirname(session_file), exist_ok=True)
    with open(session_file, "w") as f:
        f.write("invalid json")
        
    state = manager.load()
    assert isinstance(state, SessionState)
    assert state.last_agent_id is None

def test_session_manager_directory_creation(temp_workspace):
    manager = SessionManager(temp_workspace)
    state = SessionState(active_task="test")
    
    # Ensure .aegis directory doesn't exist yet
    session_dir = os.path.join(temp_workspace, ".aegis")
    assert not os.path.exists(session_dir)
    
    manager.save(state)
    
    assert os.path.exists(session_dir)
    assert os.path.exists(manager.path)
