from pathlib import Path
from unittest.mock import mock_open, patch

from aegis.infrastructure.harnesses.aider import AiderHarness


def test_aider_harness_install():
    home = Path("/tmp/home")
    harness = AiderHarness()

    with patch("pathlib.Path.home", return_value=home):
        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.write_text") as mock_write:
                harness.install_local(home)
                
                assert mock_write.called
                args, kwargs = mock_write.call_args
                assert "uvx aegis run" in args[0]


def test_aider_harness_deploy_workspace_instructions():
    with patch("pathlib.Path.write_text") as mock_write:
        harness = AiderHarness()
        harness.deploy_workspace_instructions("/workspace")
        mock_write.assert_called_once()
        args, _ = mock_write.call_args
        assert "Aegis V4 Governance" in args[0]
