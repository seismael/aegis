"""Tests for the Rule Pack model layer (pack.py)."""

from aegis.domain.policy.pack import InstalledPack, PackManifest, RulePackMeta


class TestRulePackMeta:
    def test_minimal_meta(self):
        m = RulePackMeta(name="test", version="1.0.0", description="test pack")
        assert m.name == "test"
        assert m.author == "Aegis"
        assert m.pack_type == "default"

    def test_custom_pack(self):
        m = RulePackMeta(
            name="my-pack",
            version="0.1.0",
            description="my rules",
            author="User",
            pack_type="custom",
        )
        assert m.author == "User"
        assert m.pack_type == "custom"

    def test_source_field(self):
        m = RulePackMeta(name="x", version="1", description="x", source="/some/path")
        assert m.source == "/some/path"


class TestInstalledPack:
    def test_minimal_installed(self):
        p = InstalledPack(name="arch", version="1.0.0", install_time="2025-01-01T00:00:00")
        assert p.custom_overrides == []
        assert p.files == []

    def test_with_files(self):
        p = InstalledPack(
            name="sec",
            version="2.0.0",
            install_time="2025-06-01T00:00:00",
            files=["security/rules.yaml"],
        )
        assert "security/rules.yaml" in p.files

    def test_custom_overrides(self):
        p = InstalledPack(
            name="test",
            version="1.0.0",
            install_time="2025-01-01T00:00:00",
            custom_overrides=["test-no-focused"],
        )
        assert "test-no-focused" in p.custom_overrides


class TestPackManifest:
    def test_empty_manifest(self):
        m = PackManifest()
        assert m.installed_packs == {}
        assert m.custom_files == []
        assert m.version == 1

    def test_with_packs(self):
        m = PackManifest(
            installed_packs={
                "architecture": InstalledPack(
                    name="architecture",
                    version="1.0.0",
                    install_time="2025-01-01T00:00:00",
                )
            },
            custom_files=["my-rules.yaml"],
        )
        assert "architecture" in m.installed_packs
        assert m.custom_files == ["my-rules.yaml"]

    def test_serialization_roundtrip(self):
        m = PackManifest(
            installed_packs={
                "arch": InstalledPack(
                    name="arch",
                    version="1.0.0",
                    install_time="2025-01-01T00:00:00",
                    files=["arch/rules.yaml"],
                )
            }
        )
        data = m.model_dump(mode="json")
        restored = PackManifest(**data)
        assert restored.installed_packs["arch"].name == "arch"
        assert restored.installed_packs["arch"].version == "1.0.0"
