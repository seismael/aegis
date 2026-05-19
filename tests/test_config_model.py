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

    def test_category_overrides(self):
        config = AegisConfig(
            category_overrides={"security": ["ci", "nightly"]},
        )
        assert config.category_overrides == {"security": ["ci", "nightly"]}

    def test_auto_baseline_default_false(self):
        config = AegisConfig()
        assert config.auto_baseline is False

    def test_auto_baseline_true(self):
        config = AegisConfig(auto_baseline=True)
        assert config.auto_baseline is True

    def test_max_violations_default_zero(self):
        config = AegisConfig()
        assert config.max_violations == 0

    def test_max_violations_custom(self):
        config = AegisConfig(max_violations=1000)
        assert config.max_violations == 1000


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

    def test_full_config_with_new_fields(self, tmp_path):
        aegis_dir = tmp_path / ".aegis"
        aegis_dir.mkdir()
        (aegis_dir / "config.yaml").write_text(
            yaml.dump(
                {
                    "enforcement": "warn",
                    "phase_defaults": {"style": ["pre-commit"]},
                    "category_overrides": {"security": ["ci", "nightly"]},
                    "auto_baseline": True,
                    "max_violations": 1000,
                }
            ),
            encoding="utf-8",
        )
        config = load_aegis_config(str(tmp_path))
        assert config.enforcement == "warn"
        assert config.phase_defaults == {"style": ["pre-commit"]}
        assert config.category_overrides == {"security": ["ci", "nightly"]}
        assert config.auto_baseline is True
        assert config.max_violations == 1000
