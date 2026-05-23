from unittest.mock import patch, mock_open
from pathlib import Path

from aegis.infrastructure.installer import (
    AgentNativeInstaller,
    AEGIS_GOVERNANCE_DIRECTIVE,
)


def test_installer_claude_injection():
    installer = AgentNativeInstaller()
    installer.home = Path("/tmp/aegis_test")

    mock_config = '{"mcpServers": {}}'
    with patch("builtins.open", mock_open(read_data=mock_config)):
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.print"):
                installer._inject_claude()


def test_installer_target_filter():
    installer = AgentNativeInstaller()
    installer.home = Path("/tmp/aegis_test")

    with patch.object(installer, "_inject_claude") as mock_claude:
        with patch.object(installer, "_inject_aider") as mock_aider:
            installer.install(target_tool="claude")
            mock_claude.assert_called_once()
            mock_aider.assert_not_called()


def test_installer_unsupported_tool():
    import pytest

    installer = AgentNativeInstaller()
    with pytest.raises(ValueError, match="Unsupported tool"):
        installer.install(target_tool="copilot")


def test_governance_directive_mentions_validate():
    assert "validate_architecture_compliance" in AEGIS_GOVERNANCE_DIRECTIVE
