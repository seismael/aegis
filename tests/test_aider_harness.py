from pathlib import Path
from unittest.mock import mock_open, patch
from aegis.infrastructure.harnesses.aider import AiderHarness

def test_aider_harness_install():
    home = Path("/tmp/home")
    harness = AiderHarness(home)
    
    with patch("builtins.open", mock_open()) as mocked_file:
        harness.install()
        mocked_file.assert_called_once_with(home / ".aider.conf.yml", "a")

def test_aider_harness_deploy_workspace_instructions():
    with patch("pathlib.Path.write_text") as mock_write:
        harness = AiderHarness(Path("/tmp"))
        harness.deploy_workspace_instructions("/workspace")
        mock_write.assert_called_once()
        args, _ = mock_write.call_args
        assert "Aegis V4 Governance" in args[0]
