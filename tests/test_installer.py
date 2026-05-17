import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aegis.infrastructure.installer import AegisInstaller, ClaudeAdapter, AiderAdapter


class TestAegisInstaller:
    """
    Test suite for the Aegis Universal Capability Installer.
    """

    def test_installer_initialization(self):
        installer = AegisInstaller()
        assert len(installer.adapters) >= 2
        assert any(isinstance(a, ClaudeAdapter) for a in installer.adapters)
        assert any(isinstance(a, AiderAdapter) for a in installer.adapters)

    def test_claude_adapter_is_available(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = ClaudeAdapter(".")
        
        # 1. Not available initially
        assert adapter.is_available() is False
        
        # 2. Available when .claude exists
        (tmp_path / ".claude").mkdir()
        assert adapter.is_available() is True

    def test_aider_adapter_is_available(self):
        adapter = AiderAdapter(".")
        # Aider adapter is always available for installation into home config
        assert adapter.is_available() is True

    def test_claude_adapter_manual_injection(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = ClaudeAdapter(".")
        
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        config_path = claude_dir / "claude_desktop_config.json"
        
        # Run install
        adapter.install()
        
        assert config_path.exists()
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
            assert "aegis" in config["mcpServers"]
            assert config["mcpServers"]["aegis"]["command"] == "aegis-kernel"

    def test_aider_adapter_install(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = AiderAdapter(".")
        
        config_path = tmp_path / ".aider.conf.yml"
        
        # Run install
        adapter.install()
        
        assert config_path.exists()
        with open(config_path, encoding="utf-8") as f:
            content = f.read()
            assert "mcp-server: aegis-kernel" in content

    def test_installer_orchestration(self, monkeypatch):
        mock_adapter = MagicMock()
        mock_adapter.is_available.return_value = True
        mock_adapter.install.return_value = True
        
        installer = AegisInstaller()
        installer.adapters = [mock_adapter]
        
        installer.install_globally()
        
        mock_adapter.is_available.assert_called_once()
        mock_adapter.install.assert_called_once()

    def test_entry_point_execution(self, capsys):
        # We don't want to actually install in the entry point test, 
        # so we'll just check it runs without crash.
        AegisInstaller.entry_point()
        captured = capsys.readouterr()
        assert "Aegis" in captured.out
