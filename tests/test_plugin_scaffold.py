"""Tests for the plugin scaffold generator."""

import os

import pytest

from aegis.core.plugins.scaffold import create_plugin_scaffold


class TestCreatePluginScaffold:
    """Tests for create_plugin_scaffold."""

    def test_creates_plugin_file(self, tmp_path):
        path = create_plugin_scaffold(str(tmp_path), "my-analyzer")
        assert os.path.exists(path)
        content = open(path, encoding="utf-8").read()
        assert "my-analyzer" in content
        assert "register_analyzers" in content
        assert "register_mcp_tools" in content

    def test_invalid_name_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Invalid plugin name"):
            create_plugin_scaffold(str(tmp_path), "")

    def test_name_with_spaces_raises(self, tmp_path):
        with pytest.raises(ValueError, match="Invalid plugin name"):
            create_plugin_scaffold(str(tmp_path), "my plugin")

    def test_duplicate_name_raises(self, tmp_path):
        create_plugin_scaffold(str(tmp_path), "test")
        with pytest.raises(ValueError, match="already exists"):
            create_plugin_scaffold(str(tmp_path), "test")

    def test_creates_plugin_dir(self, tmp_path):
        sub = tmp_path / "plugins"
        assert not os.path.exists(str(sub))
        create_plugin_scaffold(str(sub), "custom")
        assert os.path.exists(str(sub))
