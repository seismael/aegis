import json
from pathlib import Path
from unittest.mock import mock_open, patch
from aegis.infrastructure.harnesses.claude import ClaudeHarness

def test_claude_harness_install_new_config():
    home = Path("/tmp/home")
    harness = ClaudeHarness(home)
    
    mock_config = '{}'
    with patch("builtins.open", mock_open(read_data=mock_config)) as mocked_file:
        with patch("pathlib.Path.exists", return_value=True):
            harness.install()
            
            # Check if it tried to write the config
            handle = mocked_file()
            # The exact content depends on indent, but we can check if json.dump was called
            # or just rely on the fact that it didn't crash and called open for write.
            mocked_file.assert_any_call(home / ".claude.json", "w", encoding="utf-8")

def test_claude_harness_name():
    harness = ClaudeHarness(Path("/tmp"))
    assert harness.name == "claude"

def test_claude_harness_deploy_workspace_instructions():
    with patch("pathlib.Path.write_text") as mock_write:
        harness = ClaudeHarness(Path("/tmp"))
        harness.deploy_workspace_instructions("/workspace")
        mock_write.assert_called_once()
        args, _ = mock_write.call_args
        assert "Aegis Microkernel" in args[0]
