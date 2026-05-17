import json

import pytest

from aegis.infrastructure.installer import AegisInstaller


class TestAegisInstaller:
    """Test suite for AegisInstaller — global capability installation."""

    def test_first_time_install(self, tmp_path, monkeypatch):
        """Fresh install creates config and deploys skills."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        installer = AegisInstaller()
        installer.install_global_capability()

        # Claude config created with aegis MCP server
        assert installer.claude_config.exists()
        config = json.loads(installer.claude_config.read_text(encoding="utf-8"))
        assert "mcpServers" in config
        assert "aegis" in config["mcpServers"]
        assert config["mcpServers"]["aegis"]["command"] == "aegis-kernel"

        # Skills deployed
        assert installer.claude_skills.exists()
        deployed = list(installer.claude_skills.iterdir())
        assert any(f.name.endswith(".md") for f in deployed)

    def test_merges_existing_claude_config(self, tmp_path, monkeypatch):
        """Existing claude_desktop_config.json is merged, not overwritten."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        installer = AegisInstaller()
        installer.claude_dir.mkdir(parents=True, exist_ok=True)
        installer.claude_config.write_text(
            json.dumps({"mcpServers": {"existing-tool": {"command": "tool"}}}),
            encoding="utf-8",
        )

        installer.install_global_capability()

        config = json.loads(installer.claude_config.read_text(encoding="utf-8"))
        assert "existing-tool" in config["mcpServers"]
        assert "aegis" in config["mcpServers"]

    def test_corrupted_config_backed_up(self, tmp_path, monkeypatch):
        """Corrupted claude_desktop_config.json is backed up and recreated."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        installer = AegisInstaller()
        installer.claude_dir.mkdir(parents=True, exist_ok=True)
        installer.claude_config.write_text("{invalid json", encoding="utf-8")

        installer.install_global_capability()

        # Backup created
        assert installer.claude_config.with_suffix(".json.bak").exists()
        # New config created with aegis
        config = json.loads(installer.claude_config.read_text(encoding="utf-8"))
        assert "aegis" in config["mcpServers"]

    def test_idempotent_reinstall(self, tmp_path, monkeypatch):
        """Reinstalling does not duplicate the aegis MCP entry."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        installer = AegisInstaller()
        installer.install_global_capability()
        installer.install_global_capability()

        config = json.loads(installer.claude_config.read_text(encoding="utf-8"))
        # The aegis entry exists exactly once (dict key, not list)
        assert list(config["mcpServers"].keys()).count("aegis") == 1

    def test_aider_config_created(self, tmp_path, monkeypatch):
        """Aider config created with mcp-server directive."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        installer = AegisInstaller()
        installer.install_global_capability()

        assert installer.aider_config.exists()
        content = installer.aider_config.read_text(encoding="utf-8")
        assert "aegis-kernel" in content
        assert "mcp-server:" in content

    def test_aider_config_skips_when_present(self, tmp_path, monkeypatch):
        """Aider config not modified when aegis-kernel already present."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        installer = AegisInstaller()
        installer.aider_config.parent.mkdir(parents=True, exist_ok=True)
        installer.aider_config.write_text(
            "mcp-server: aegis-kernel --transport stdio\nother: value\n",
            encoding="utf-8",
        )

        installer.install_global_capability()

        content = installer.aider_config.read_text(encoding="utf-8")
        # Only one occurrence
        assert content.count("aegis-kernel") == 1
        # Original content preserved
        assert "other: value" in content

    def test_skills_deployed(self, tmp_path, monkeypatch):
        """Skill markdown files are copied to .claude/skills/."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        installer = AegisInstaller()
        installer.install_global_capability()

        skill_files = list(installer.claude_skills.iterdir())
        skill_names = {f.name for f in skill_files}
        # At least one skill deployed
        assert len(skill_names) >= 1
        assert any(n.endswith(".md") for n in skill_names)

    def test_directories_created(self, tmp_path, monkeypatch):
        """Required directories are created during install."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        installer = AegisInstaller()
        installer.install_global_capability()

        assert installer.claude_dir.exists()
        assert installer.claude_skills.exists()

    def test_entry_point_prints_message(self, tmp_path, monkeypatch, capsys):
        """entry_point prints success message without crashing."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        AegisInstaller.entry_point()
        captured = capsys.readouterr()
        assert "Global Capability Installed" in captured.out

    def test_empty_claude_config_no_mcp_servers(self, tmp_path, monkeypatch):
        """Existing config without mcpServers key gets it added."""
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        installer = AegisInstaller()
        installer.claude_dir.mkdir(parents=True, exist_ok=True)
        installer.claude_config.write_text(
            json.dumps({"other_key": "value"}), encoding="utf-8"
        )

        installer.install_global_capability()

        config = json.loads(installer.claude_config.read_text(encoding="utf-8"))
        assert "mcpServers" in config
        assert "aegis" in config["mcpServers"]
        assert config["other_key"] == "value"
