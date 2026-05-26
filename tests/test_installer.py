from pathlib import Path
from unittest.mock import MagicMock, patch

from aegis.infrastructure.installer import (
    AEGIS_GOVERNANCE_DIRECTIVE,
    AgentNativeInstaller,
)


def test_installer_claude_harness_usage():
    installer = AgentNativeInstaller()
    
    mock_harness = MagicMock()
    installer.harnesses["claude"] = mock_harness
    
    installer.install(target_tool="claude")
    
    mock_harness.install.assert_called_once()
    mock_harness.deploy_skills.assert_called_once()


def test_installer_target_filter():
    installer = AgentNativeInstaller()
    
    mock_claude = MagicMock()
    mock_aider = MagicMock()
    installer.harnesses = {
        "claude": mock_claude,
        "aider": mock_aider
    }

    installer.install(target_tool="claude")
    mock_claude.install.assert_called_once()
    mock_aider.install.assert_not_called()


def test_installer_unsupported_tool():
    import pytest

    installer = AgentNativeInstaller()
    with pytest.raises(ValueError, match="Unsupported tool"):
        installer.install(target_tool="copilot")


def test_governance_directive_mentions_validate():
    assert "validate_architecture_compliance" in AEGIS_GOVERNANCE_DIRECTIVE
