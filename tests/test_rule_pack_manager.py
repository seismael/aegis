"""Tests for RulePackManager lifecycle operations."""

import json
import os

from aegis.domain.policy.pack import RulePackMeta
from aegis.domain.policy.pack_manager import RulePackManager


class TestRulePackManager:
    """Tests for RulePackManager using tmp_path workspace."""

    def _manager(self, tmp_path):
        rules_dir = tmp_path / ".aegis" / "rules"
        rules_dir.mkdir(parents=True)
        return RulePackManager(str(rules_dir))

    # --- Query ---

    def test_list_available_returns_packs(self, tmp_path):
        mgr = self._manager(tmp_path)
        available = mgr.list_available()
        assert len(available) >= 6
        assert "architecture" in available
        assert "security" in available
        assert "testing" in available
        assert "style" in available
        assert "best-practices" in available
        assert "design" in available

    def test_list_available_returns_meta(self, tmp_path):
        mgr = self._manager(tmp_path)
        meta = mgr.list_available()["architecture"]
        assert isinstance(meta, RulePackMeta)
        assert meta.version == "1.0.0"
        assert meta.author == "Aegis"

    def test_list_installed_empty_initially(self, tmp_path):
        mgr = self._manager(tmp_path)
        assert mgr.list_installed() == {}

    def test_list_custom_empty_initially(self, tmp_path):
        mgr = self._manager(tmp_path)
        assert mgr.list_custom() == []

    def test_list_custom_detects_root_files(self, tmp_path):
        rules_dir = tmp_path / ".aegis" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "my-custom.yaml").write_text(
            "rules:\n  - id: test\n", encoding="utf-8"
        )
        mgr = RulePackManager(str(rules_dir))
        custom = mgr.list_custom()
        assert "my-custom.yaml" in custom

    def test_is_installed_false_initially(self, tmp_path):
        mgr = self._manager(tmp_path)
        assert not mgr.is_installed("architecture")

    # --- Install ---

    def test_install_creates_pack_dir(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.install("architecture")
        rules_dir = tmp_path / ".aegis" / "rules"
        assert (rules_dir / "architecture").is_dir()
        assert (rules_dir / "architecture" / "rules.yaml").is_file()
        assert not (
            rules_dir / "architecture" / "pack.yaml"
        ).is_file()  # metadata skipped

    def test_install_updates_manifest(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.install("architecture")
        manifest = mgr._load_manifest()
        assert "architecture" in manifest.installed_packs
        assert manifest.installed_packs["architecture"].version == "1.0.0"

    def test_install_is_installed_true(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.install("architecture")
        assert mgr.is_installed("architecture")

    def test_install_unknown_pack_raises(self, tmp_path):
        mgr = self._manager(tmp_path)
        import pytest

        with pytest.raises(ValueError, match="Unknown rule pack"):
            mgr.install("nonexistent")

    def test_install_twice_raises(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.install("architecture")
        import pytest

        with pytest.raises(ValueError, match="already installed"):
            mgr.install("architecture")

    def test_install_rule_content(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.install("testing")
        rules_file = tmp_path / ".aegis" / "rules" / "testing" / "rules.yaml"
        content = rules_file.read_text(encoding="utf-8")
        assert "test-no-focused" in content
        assert "test-naming-convention" in content

    # --- Remove ---

    def test_remove_deletes_pack_dir(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.install("style")
        rules_dir = tmp_path / ".aegis" / "rules"
        assert (rules_dir / "style").is_dir()
        mgr.remove("style")
        assert not (rules_dir / "style").is_dir()

    def test_remove_clears_manifest_entry(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.install("style")
        mgr.remove("style")
        assert not mgr.is_installed("style")

    def test_remove_not_installed_raises(self, tmp_path):
        mgr = self._manager(tmp_path)
        import pytest

        with pytest.raises(ValueError, match="not installed"):
            mgr.remove("nonexistent")

    def test_remove_unknown_raises(self, tmp_path):
        mgr = self._manager(tmp_path)
        import pytest

        with pytest.raises(ValueError, match="not installed"):
            mgr.remove("nonexistent")

    # --- Update ---

    def test_update_all(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.install("architecture")
        mgr.install("security")
        updated = mgr.update()
        # Both should be listed (or empty if up to date)
        assert isinstance(updated, list)

    def test_update_single_pack(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.install("architecture")
        updated = mgr.update("architecture")
        assert isinstance(updated, list)

    def test_update_not_installed_skips(self, tmp_path):
        mgr = self._manager(tmp_path)
        updated = mgr.update("architecture")
        assert updated == []

    # --- Reset ---

    def test_reset_removes_all_packs(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.install("architecture")
        mgr.install("security")
        mgr.install("testing")
        mgr.reset()
        assert mgr.list_installed() == {}

    def test_reset_preserves_custom_root_files(self, tmp_path):
        rules_dir = tmp_path / ".aegis" / "rules"
        rules_dir.mkdir(parents=True)
        custom = rules_dir / "my-rules.yaml"
        custom.write_text("rules: []", encoding="utf-8")
        mgr = RulePackManager(str(rules_dir))
        mgr.install("architecture")
        mgr.reset()
        assert custom.is_file(), "Custom root files should survive reset"

    def test_reset_empty_manifest_no_crash(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.reset()  # no-op, should not crash

    # --- Create ---

    def test_create_custom_pack(self, tmp_path):
        mgr = self._manager(tmp_path)
        rules = [
            {
                "id": "my-rule",
                "description": "test",
                "engine_type": "regex",
                "query": "test",
            }
        ]
        path = mgr.create("my-pack", rules)
        assert os.path.isdir(path)
        rules_file = os.path.join(path, "rules.yaml")
        assert os.path.isfile(rules_file)
        assert mgr.is_installed("my-pack")

    def test_create_pack_manifest_type(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.create("custom-pack", [{"id": "r1", "description": "r1"}])
        manifest = mgr._load_manifest()
        assert manifest.installed_packs["custom-pack"].version == "1.0.0"

    def test_create_duplicate_raises(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.create("dup-pack", [])
        import pytest

        with pytest.raises(ValueError, match="already exists"):
            mgr.create("dup-pack", [])

    def test_create_invalid_name_raises(self, tmp_path):
        mgr = self._manager(tmp_path)
        import pytest

        with pytest.raises(ValueError, match="Pack name"):
            mgr.create("../escape", [])

    # --- Install defaults ---

    def test_install_defaults_all(self, tmp_path):
        mgr = self._manager(tmp_path)
        installed = mgr.install_defaults()
        assert len(installed) >= 6
        assert "architecture" in installed

    def test_install_defaults_idempotent(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.install_defaults()
        second = mgr.install_defaults()
        # Second call should install nothing new
        assert len(second) == 0

    def test_install_defaults_subset(self, tmp_path):
        mgr = self._manager(tmp_path)
        installed = mgr.install_defaults(["architecture", "security"])
        assert set(installed) == {"architecture", "security"}
        assert "testing" not in installed

    # --- Manifest persistence ---

    def test_manifest_persists_across_instances(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.install("architecture")
        # Create new manager pointing to same dir
        mgr2 = RulePackManager(str(tmp_path / ".aegis" / "rules"))
        assert mgr2.is_installed("architecture")
        assert mgr2.list_installed()["architecture"].version == "1.0.0"

    def test_manifest_json_format(self, tmp_path):
        mgr = self._manager(tmp_path)
        mgr.install("security")
        manifest_path = tmp_path / ".aegis" / "rules" / ".packs.json"
        assert manifest_path.is_file()
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert "installed_packs" in data
        assert "security" in data["installed_packs"]

    # --- Edge cases ---

    def test_rules_dir_does_not_exist(self, tmp_path):
        """Manager should handle non-existent rules dir gracefully."""
        mgr = RulePackManager(str(tmp_path / "nonexistent"))
        assert mgr.list_installed() == {}
        assert mgr.list_custom() == []

    def test_corrupt_manifest_starts_fresh(self, tmp_path):
        rules_dir = tmp_path / ".aegis" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / ".packs.json").write_text("{{{ corrupt", encoding="utf-8")
        mgr = RulePackManager(str(rules_dir))
        assert mgr.list_installed() == {}

    def test_mixed_custom_and_pack_files(self, tmp_path):
        """Root-level custom files coexist with installed pack directories."""
        rules_dir = tmp_path / ".aegis" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "legacy.yaml").write_text(
            "rules:\n  - id: legacy\n", encoding="utf-8"
        )
        mgr = RulePackManager(str(rules_dir))
        mgr.install("architecture")
        custom = mgr.list_custom()
        assert "legacy.yaml" in custom
