"""Tests for AegisConfig loading and merging."""


import yaml

from aegis.core.container.config_loader import load_aegis_config
from aegis.core.models.config import AegisConfig


class TestAegisConfig:
    """Tests for AegisConfig model."""

    def test_defaults(self):
        config = AegisConfig()
        assert config.enforcement == "warn"
        assert config.phase_defaults is None

    def test_phase_defaults_custom(self):
        config = AegisConfig(
            enforcement="block",
            phase_defaults={"security": ["ci", "nightly"]},
        )
        assert config.enforcement == "block"
        assert config.phase_defaults == {"security": ["ci", "nightly"]}


class TestConfigLoader:
    """Tests for load_aegis_config()."""

    def test_missing_file_returns_defaults(self, tmp_path):
        config = load_aegis_config(str(tmp_path))
        assert config.enforcement == "warn"
        assert config.phase_defaults is None

    def test_empty_file_returns_defaults(self, tmp_path):
        aegis_dir = tmp_path / ".aegis"
        aegis_dir.mkdir()
        (aegis_dir / "config.yaml").write_text("", encoding="utf-8")
        config = load_aegis_config(str(tmp_path))
        assert config.enforcement == "warn"

    def test_full_config_loads(self, tmp_path):
        aegis_dir = tmp_path / ".aegis"
        aegis_dir.mkdir()
        (aegis_dir / "config.yaml").write_text(
            yaml.dump(
                {
                    "enforcement": "block",
                    "phase_defaults": {
                        "style": ["pre-commit"],
                        "security": ["ci", "on-demand"],
                    },
                }
            ),
            encoding="utf-8",
        )
        config = load_aegis_config(str(tmp_path))
        assert config.enforcement == "block"
        assert config.phase_defaults == {
            "style": ["pre-commit"],
            "security": ["ci", "on-demand"],
        }

    def test_invalid_yaml_returns_defaults(self, tmp_path):
        aegis_dir = tmp_path / ".aegis"
        aegis_dir.mkdir()
        (aegis_dir / "config.yaml").write_text("not: valid: yaml: [[", encoding="utf-8")
        config = load_aegis_config(str(tmp_path))
        assert config.enforcement == "warn"
