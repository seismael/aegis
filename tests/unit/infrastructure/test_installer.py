from unittest.mock import MagicMock

from aegis.infrastructure.harnesses.base import AEGIS_GOVERNANCE_DIRECTIVE
from aegis.infrastructure.installer import (
    AgentNativeInstaller,
)


def test_installer_claude_harness_usage():
    installer = AgentNativeInstaller()

    mock_harness = MagicMock()
    installer.harnesses["claude"] = mock_harness

    installer.init_workspace(target_tool="claude")

    mock_harness.install_local.assert_called_once()
    mock_harness.deploy_skills_local.assert_called_once()


def test_installer_gemini_harness_usage():
    installer = AgentNativeInstaller()

    mock_harness = MagicMock()
    installer.harnesses["gemini"] = mock_harness

    installer.init_workspace(target_tool="gemini")

    mock_harness.install_local.assert_called_once()
    mock_harness.deploy_skills_local.assert_called_once()


def test_installer_target_filter():
    installer = AgentNativeInstaller()

    mock_claude = MagicMock()
    mock_aider = MagicMock()
    installer.harnesses = {"claude": mock_claude, "aider": mock_aider}

    installer.init_workspace(target_tool="claude")
    mock_claude.install_local.assert_called_once()
    mock_aider.install_local.assert_not_called()


def test_installer_unsupported_tool():
    import pytest

    installer = AgentNativeInstaller()
    with pytest.raises(ValueError, match="Unsupported tool"):
        installer.init_workspace(target_tool="copilot")


def test_governance_directive_mentions_validate():
    assert "validate_architecture_compliance" in AEGIS_GOVERNANCE_DIRECTIVE
