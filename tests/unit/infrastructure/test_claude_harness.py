from pathlib import Path
from unittest.mock import mock_open, patch

from aegis.infrastructure.harnesses.claude import ClaudeHarness


def test_claude_harness_install_new_config():
    home = Path("/tmp/home")
    harness = ClaudeHarness()

    mock_config = "{}"
    with patch("pathlib.Path.home", return_value=home):
        with patch("builtins.open", mock_open(read_data=mock_config)) as mocked_file:
            with patch("pathlib.Path.exists", return_value=True):
                harness.install_local(home)

                mocked_file()
                mocked_file.assert_any_call(
                    home / ".claude.json", "w", encoding="utf-8"
                )


def test_claude_harness_name():
    harness = ClaudeHarness()
    assert harness.name == "claude"


def test_claude_harness_deploy_workspace_instructions():
    with patch("pathlib.Path.write_text") as mock_write:
        harness = ClaudeHarness()
        harness.deploy_workspace_instructions("/workspace")
        mock_write.assert_called_once()
        args, _ = mock_write.call_args
        assert "Aegis Microkernel" in args[0]
