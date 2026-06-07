"""Tests for AegisConfig model."""

from aegis.domain.policy.config import AegisConfig


class TestAegisConfig:
    """Tests for AegisConfig model."""

    def test_defaults(self):
        config = AegisConfig()
        assert config.enforcement == "block"
        assert config.max_violations == 1000
        assert config.phase_defaults == {}
        assert config.category_overrides == {}

    def test_phase_defaults_custom(self):
        config = AegisConfig(phase_defaults={"security": ["ci", "nightly"]})
        assert config.phase_defaults == {"security": ["ci", "nightly"]}

    def test_category_overrides(self):
        config = AegisConfig(category_overrides={"security": ["ci", "nightly"]})
        assert config.category_overrides == {"security": ["ci", "nightly"]}

    def test_auto_baseline_default_false(self):
        config = AegisConfig()
        assert config.auto_baseline is False

    def test_auto_baseline_true(self):
        config = AegisConfig(auto_baseline=True)
        assert config.auto_baseline is True

    def test_max_violations_default(self):
        config = AegisConfig()
        assert config.max_violations == 1000

    def test_max_violations_custom(self):
        config = AegisConfig(max_violations=10)
        assert config.max_violations == 10

    def test_missing_file_returns_defaults(self):
        config = AegisConfig()
        assert config.enforcement == "block"
        assert config.max_violations == 1000

    def test_empty_file_returns_defaults(self):
        config = AegisConfig()
        assert config.enforcement == "block"
        assert config.max_violations == 1000

    def test_full_config_loads(self):
        config = AegisConfig(
            enforcement="block",
            phase_defaults={
                "style": ["pre-commit"],
                "security": ["ci", "on-demand"],
            },
        )
        assert config.enforcement == "block"
        assert config.phase_defaults == {
            "style": ["pre-commit"],
            "security": ["ci", "on-demand"],
        }

    def test_yaml_roundtrip(self):
        config = AegisConfig(
            enforcement="warn",
            phase_defaults={"style": ["pre-commit"]},
            category_overrides={"security": ["ci", "nightly"]},
            auto_baseline=True,
            max_violations=1000,
        )
        assert config.enforcement == "warn"
        assert config.phase_defaults == {"style": ["pre-commit"]}
        assert config.category_overrides == {"security": ["ci", "nightly"]}
        assert config.auto_baseline is True
        assert config.max_violations == 1000
