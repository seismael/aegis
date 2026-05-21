import json
from unittest.mock import MagicMock, patch

from aegis.infrastructure.adapters.aider import AiderAdapter
from aegis.infrastructure.adapters.base import ToolAdapter
from aegis.infrastructure.adapters.claude import ClaudeAdapter
from aegis.infrastructure.adapters.generic import GenericMCPAdapter
from aegis.infrastructure.adapters.opendevin import OpenDevinAdapter


class TestClaudeAdapter:
    """Unit tests for ClaudeAdapter."""

    def test_name(self):
        adapter = ClaudeAdapter(".")
        assert adapter.name == "Claude"

    def test_is_present_false(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = ClaudeAdapter(".")
        assert adapter.is_present() is False

    def test_is_present_true(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        (tmp_path / ".claude").mkdir()
        adapter = ClaudeAdapter(".")
        assert adapter.is_present() is True

    def test_install_fallback_manual_injection(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = ClaudeAdapter(".")

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        config_path = claude_dir / "claude_desktop_config.json"

        adapter.install()

        assert config_path.exists()
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
            assert "aegis" in config["mcpServers"]
            assert config["mcpServers"]["aegis"]["command"] == "aegis-kernel"

    def test_install_prefers_native_cli(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = ClaudeAdapter(".")
        (tmp_path / ".claude").mkdir()

        with patch.object(adapter, "_try_native_mcp_add", return_value=True) as native:
            with patch.object(adapter, "_deploy_skills") as deploy:
                adapter.install()
                native.assert_called_once()
                deploy.assert_called_once()

    def test_uninstall_native_cli(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = ClaudeAdapter(".")

        with patch.object(
            adapter, "_try_native_mcp_remove", return_value=True
        ) as native:
            with patch.object(adapter, "_remove_skills") as rm_skills:
                adapter.uninstall()
                native.assert_called_once()
                rm_skills.assert_called_once()

    def test_uninstall_fallback_manual_removal(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = ClaudeAdapter(".")

        config_path = tmp_path / ".claude" / "claude_desktop_config.json"
        config_path.parent.mkdir(parents=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"mcpServers": {"aegis": {"command": "aegis-kernel"}}}, f)

        with patch.object(adapter, "_try_native_mcp_remove", return_value=False):
            with patch.object(adapter, "_remove_skills"):
                adapter.uninstall()

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
            assert "aegis" not in config.get("mcpServers", {})

    def test_uninstall_no_config_no_crash(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = ClaudeAdapter(".")
        with patch.object(adapter, "_try_native_mcp_remove", return_value=False):
            with patch.object(adapter, "_remove_skills"):
                result = adapter.uninstall()
                assert result is True

    def test_native_mcp_add_success(self):
        adapter = ClaudeAdapter(".")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            assert adapter._try_native_mcp_add() is True
            mock_run.assert_called_once_with(
                [
                    "claude",
                    "mcp",
                    "add",
                    "aegis",
                    "aegis-kernel",
                    "--",
                    "--transport",
                    "stdio",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_native_mcp_add_cli_not_found(self):
        adapter = ClaudeAdapter(".")
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert adapter._try_native_mcp_add() is False

    def test_native_mcp_remove_success(self):
        adapter = ClaudeAdapter(".")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            assert adapter._try_native_mcp_remove() is True
            mock_run.assert_called_once_with(
                ["claude", "mcp", "remove", "aegis"],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_manual_config_injection_updates_existing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = ClaudeAdapter(".")
        config_path = tmp_path / ".claude" / "claude_desktop_config.json"
        config_path.parent.mkdir(parents=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump({"mcpServers": {"other": {"command": "other"}}}, f)

        adapter._manual_config_injection()

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
            assert "aegis" in config["mcpServers"]
            assert "other" in config["mcpServers"]

    def test_manual_config_injection_bad_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = ClaudeAdapter(".")
        config_path = tmp_path / ".claude" / "claude_desktop_config.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text("{invalid json", encoding="utf-8")

        adapter._manual_config_injection()

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
            assert "aegis" in config["mcpServers"]

    def test_deploy_skills(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = ClaudeAdapter(".")

        # Real source file for the traversable to return
        src_dir = tmp_path / "skill_src"
        src_dir.mkdir()
        src_file = src_dir / "aegis-evaluate.md"
        src_file.write_text("# evaluate skill", encoding="utf-8")

        mock_traversable = MagicMock()
        mock_traversable.iterdir.return_value = [src_file]

        with patch("importlib.resources.files", return_value=mock_traversable):
            adapter._deploy_skills()

        dest = tmp_path / ".claude" / "skills" / "aegis-evaluate.md"
        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == "# evaluate skill"

    def test_remove_skills(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = ClaudeAdapter(".")

        # Create a skill file first
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        skill_file = skills_dir / "aegis-evaluate.md"
        skill_file.write_text("test", encoding="utf-8")

        mock_traversable = MagicMock()
        mock_item = MagicMock()
        mock_item.name = "aegis-evaluate.md"
        mock_item.endswith.side_effect = lambda s: s == ".md"
        mock_traversable.iterdir.return_value = [mock_item]

        with patch("importlib.resources.files", return_value=mock_traversable):
            adapter._remove_skills()

        assert not skill_file.exists()


class TestAiderAdapter:
    """Unit tests for AiderAdapter."""

    def test_name(self):
        adapter = AiderAdapter(".")
        assert adapter.name == "Aider"

    def test_install_creates_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = AiderAdapter(".")
        config_path = tmp_path / ".aider.conf.yml"

        adapter.install()

        assert config_path.exists()
        content = config_path.read_text(encoding="utf-8")
        assert "mcp-server: aegis-kernel" in content

    def test_install_skips_if_already_present(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = AiderAdapter(".")
        config_path = tmp_path / ".aider.conf.yml"
        config_path.write_text("mcp-server: aegis-kernel\n", encoding="utf-8")

        adapter.install()

        content = config_path.read_text(encoding="utf-8")
        assert content.count("aegis-kernel") == 1

    def test_uninstall_removes_aegis_line(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = AiderAdapter(".")
        config_path = tmp_path / ".aider.conf.yml"
        config_path.write_text(
            "key: val\nmcp-server: aegis-kernel\nother: val\n", encoding="utf-8"
        )

        adapter.uninstall()

        content = config_path.read_text(encoding="utf-8")
        assert "aegis-kernel" not in content
        assert "key: val" in content
        assert "other: val" in content

    def test_uninstall_no_config_no_crash(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = AiderAdapter(".")
        result = adapter.uninstall()
        assert result is True

    def test_is_present_returns_false_when_cli_missing_and_no_config(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        adapter = AiderAdapter(".")
        with patch("shutil.which", return_value=None):
            assert adapter.is_present() is False


class TestOpenDevinAdapter:
    """Unit tests for OpenDevinAdapter."""

    def test_name(self):
        adapter = OpenDevinAdapter(".")
        assert adapter.name == "OpenDevin"

    def test_install_creates_config(self, tmp_path):
        adapter = OpenDevinAdapter(str(tmp_path))
        config_path = tmp_path / "config.toml"

        adapter.install()

        assert config_path.exists()
        content = config_path.read_text(encoding="utf-8")
        assert "aegis-kernel" in content
        assert 'name = "aegis"' in content

    def test_install_skips_if_already_present(self, tmp_path):
        adapter = OpenDevinAdapter(str(tmp_path))
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            'name = "aegis"\ncommand = "aegis-kernel"\n', encoding="utf-8"
        )

        adapter.install()

        content = config_path.read_text(encoding="utf-8")
        # The section was not duplicated
        assert content.count("aegis-kernel") == 1
        assert content.count('name = "aegis"') == 1

    def test_uninstall_removes_aegis_block(self, tmp_path):
        adapter = OpenDevinAdapter(str(tmp_path))
        config_path = tmp_path / "config.toml"
        config_path.write_text(
            '[[mcp_servers]]\nname = "aegis"\ncommand = "uv"\nargs = []\n\n'
            '[[mcp_servers]]\nname = "other"\ncommand = "x"\n',
            encoding="utf-8",
        )

        adapter.uninstall()

        content = config_path.read_text(encoding="utf-8")
        assert 'name = "aegis"' not in content
        assert 'name = "other"' in content

    def test_uninstall_no_config_no_crash(self, tmp_path):
        adapter = OpenDevinAdapter(str(tmp_path))
        result = adapter.uninstall()
        assert result is True

    def test_uninstall_oserror_returns_false(self, tmp_path):
        adapter = OpenDevinAdapter(str(tmp_path))
        config_path = tmp_path / "config.toml"
        config_path.write_text("content", encoding="utf-8")
        with patch("builtins.open", side_effect=OSError):
            result = adapter.uninstall()
            assert result is False


class TestGenericMCPAdapter:
    """Unit tests for GenericMCPAdapter."""

    def test_name(self):
        adapter = GenericMCPAdapter(".")
        assert adapter.name == "Generic MCP"

    def test_install_creates_manifest(self, tmp_path):
        adapter = GenericMCPAdapter(str(tmp_path))
        manifest_path = tmp_path / "mcp.json"

        adapter.install()

        assert manifest_path.exists()
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
            assert "aegis" in data["mcpServers"]
            assert data["mcpServers"]["aegis"]["command"] == "uv"

    def test_install_merges_existing_manifest(self, tmp_path):
        adapter = GenericMCPAdapter(str(tmp_path))
        manifest_path = tmp_path / "mcp.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump({"mcpServers": {"existing": {"command": "x"}}}, f)

        adapter.install()

        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
            assert "aegis" in data["mcpServers"]
            assert "existing" in data["mcpServers"]

    def test_install_skips_if_aegis_already_present(self, tmp_path):
        adapter = GenericMCPAdapter(str(tmp_path))
        manifest_path = tmp_path / "mcp.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump({"mcpServers": {"aegis": {"command": "uv"}}}, f)

        adapter.install()

        # Should not modify the file
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
            assert len(data["mcpServers"]) == 1

    def test_uninstall_removes_aegis_from_manifest(self, tmp_path):
        adapter = GenericMCPAdapter(str(tmp_path))
        manifest_path = tmp_path / "mcp.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(
                {"mcpServers": {"aegis": {"command": "uv"}, "other": {"command": "x"}}},
                f,
            )

        adapter.uninstall()

        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
            assert "aegis" not in data["mcpServers"]
            assert "other" in data["mcpServers"]

    def test_uninstall_no_manifest_no_crash(self, tmp_path):
        adapter = GenericMCPAdapter(str(tmp_path))
        result = adapter.uninstall()
        assert result is True

    def test_is_present_always_true(self):
        adapter = GenericMCPAdapter(".")
        assert adapter.is_present() is True


class TestToolAdapterBase:
    """Tests for ToolAdapter abstract base."""

    def test_cannot_instantiate_base(self):
        with patch.multiple(ToolAdapter, __abstractmethods__=set()):
            instance = ToolAdapter(".")
            assert instance.target_dir is not None
            instance.log_success()

    def test_log_success(self):
        adapter = ClaudeAdapter(".")
        with patch("aegis.infrastructure.adapters.base.logger.info") as mock_log:
            adapter.log_success()
            mock_log.assert_called_once_with(
                "Successfully installed Aegis capability into Claude"
            )
