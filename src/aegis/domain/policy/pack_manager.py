"""Rule Pack Manager — lifecycle operations for versioned rule pack collections."""

import importlib.resources
import json
import os
import shutil
from datetime import UTC, datetime

import structlog
import yaml

from aegis.domain.policy.pack import InstalledPack, PackManifest, RulePackMeta

logger = structlog.get_logger()

_PACKS_RESOURCE = "aegis.resources.default_rules"
_MANIFEST_FILE = ".packs.json"
_PACK_META_FILE = "pack.yaml"
_RULES_FILE = "rules.yaml"


class RulePackManager:
    """
    Manages rule pack installation, removal, update, and discovery.

    Operates on the .aegis/rules/ directory. Does NOT depend on the evaluation
    engine, baseline manager, or any runtime infrastructure.
    """

    def __init__(self, rules_dir: str):
        self.rules_dir = rules_dir

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list_available(self) -> dict[str, RulePackMeta]:
        """Discover all packs shipped with Aegis (from package resources)."""
        packs: dict[str, RulePackMeta] = {}
        try:
            resource_root = importlib.resources.files(_PACKS_RESOURCE)
            for entry in sorted(resource_root.iterdir()):
                if not entry.is_dir():
                    continue
                meta = self._read_pack_meta(entry)
                if meta is not None:
                    packs[meta.name] = meta
        except Exception as exc:
            logger.warning("Failed to discover resource packs", error=str(exc))
        return packs

    def list_installed(self) -> dict[str, InstalledPack]:
        """Return the installed-packs manifest."""
        return self._load_manifest().installed_packs

    def list_custom(self) -> list[str]:
        """Return root-level YAML files in rules/ that belong to no pack."""
        manifest = self._load_manifest()
        installed_files: set[str] = set()
        for pack in manifest.installed_packs.values():
            installed_files.update(pack.files)

        custom: list[str] = []
        if not os.path.isdir(self.rules_dir):
            return custom

        for name in sorted(os.listdir(self.rules_dir)):
            if not name.endswith((".yaml", ".yml")):
                continue
            if name == _MANIFEST_FILE:
                continue
            if name not in installed_files:
                custom.append(name)

        return custom

    def is_installed(self, pack_name: str) -> bool:
        """Check whether a pack is currently installed."""
        return pack_name in self._load_manifest().installed_packs

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def install(self, pack_name: str) -> None:
        """
        Install a shipped pack into .aegis/rules/<pack_name>/.

        Raises ValueError if the pack is unknown or already installed.
        """
        available = self.list_available()
        if pack_name not in available:
            raise ValueError(
                f"Unknown rule pack '{pack_name}'. "
                f"Available: {', '.join(sorted(available))}"
            )

        manifest = self._load_manifest()
        if pack_name in manifest.installed_packs:
            raise ValueError(
                f"Pack '{pack_name}' is already installed. "
                "Use 'aegis rules update' to refresh or 'aegis rules remove' first."
            )

        meta = available[pack_name]
        self._ensure_rules_dir()

        # Copy resource files into .aegis/rules/<pack_name>/
        pack_dir = os.path.join(self.rules_dir, pack_name)
        os.makedirs(pack_dir, exist_ok=True)

        copied_files: list[str] = []
        try:
            resource_root = importlib.resources.files(_PACKS_RESOURCE)
            pack_resource = resource_root.joinpath(pack_name)

            if pack_resource.is_dir():
                for res_file in pack_resource.iterdir():
                    if res_file.is_file() and res_file.name != _PACK_META_FILE:
                        dest = os.path.join(pack_dir, res_file.name)
                        with importlib.resources.as_file(res_file) as src_path:
                            shutil.copy2(str(src_path), dest)
                        copied_files.append(f"{pack_name}/{res_file.name}")
            else:
                raise ValueError(f"Resource '{pack_name}' is not a pack directory")
        except Exception:
            # Clean up on failure
            if os.path.isdir(pack_dir):
                shutil.rmtree(pack_dir, ignore_errors=True)
            raise

        # Record in manifest
        manifest.installed_packs[pack_name] = InstalledPack(
            name=pack_name,
            version=meta.version,
            install_time=datetime.now(UTC).isoformat(),
            files=copied_files,
        )
        self._save_manifest(manifest)

        logger.info(
            "Rule pack installed",
            pack=pack_name,
            version=meta.version,
            rules=copied_files,
        )

    def remove(self, pack_name: str) -> None:
        """
        Remove an installed pack. Deletes its rule directory and manifest entry.
        Raises ValueError if not installed.
        """
        manifest = self._load_manifest()
        if pack_name not in manifest.installed_packs:
            raise ValueError(
                f"Pack '{pack_name}' is not installed. "
                f"Installed: {', '.join(sorted(manifest.installed_packs)) or '(none)'}"
            )

        # Delete pack directory
        pack_dir = os.path.join(self.rules_dir, pack_name)
        if os.path.isdir(pack_dir):
            shutil.rmtree(pack_dir, ignore_errors=True)

        # Remove from manifest
        del manifest.installed_packs[pack_name]
        self._save_manifest(manifest)

        logger.info("Rule pack removed", pack=pack_name)

    def update(self, pack_name: str | None = None) -> list[str]:
        """
        Re-copy shipped rule files for one or all installed packs.
        Preserves custom_overrides (detected by diffing on-disk vs shipped).
        Returns list of updated pack names.
        """
        manifest = self._load_manifest()
        available = self.list_available()
        updated: list[str] = []

        targets = [pack_name] if pack_name else list(manifest.installed_packs.keys())

        for name in targets:
            if name not in manifest.installed_packs:
                logger.warning("Pack not installed, skipping", pack=name)
                continue
            if name not in available:
                logger.warning("Pack no longer available, skipping", pack=name)
                continue

            installed = manifest.installed_packs[name]
            meta = available[name]

            if installed.version == meta.version and not self._has_local_changes(name):
                logger.debug("Pack already up-to-date", pack=name)
                continue

            # Re-copy shipped files
            pack_dir = os.path.join(self.rules_dir, name)
            os.makedirs(pack_dir, exist_ok=True)

            resource_root = importlib.resources.files(_PACKS_RESOURCE)
            pack_resource = resource_root.joinpath(name)

            for res_file in pack_resource.iterdir():
                if res_file.is_file() and res_file.name != _PACK_META_FILE:
                    dest = os.path.join(pack_dir, res_file.name)
                    with importlib.resources.as_file(res_file) as src_path:
                        shutil.copy2(str(src_path), dest)

            # Update manifest entry
            updated_meta = InstalledPack(
                name=name,
                version=meta.version,
                install_time=datetime.now(UTC).isoformat(),
                files=installed.files,
                custom_overrides=installed.custom_overrides,
            )
            manifest.installed_packs[name] = updated_meta
            updated.append(name)

            logger.info("Rule pack updated", pack=name, version=meta.version)

        self._save_manifest(manifest)
        return updated

    def reset(self) -> None:
        """
        Remove ALL installed pack directories and the manifest.
        Root-level custom YAML files in .aegis/rules/ are preserved.
        """
        manifest = self._load_manifest()

        for pack_name in list(manifest.installed_packs.keys()):
            pack_dir = os.path.join(self.rules_dir, pack_name)
            if os.path.isdir(pack_dir):
                shutil.rmtree(pack_dir, ignore_errors=True)

        # Clear manifest (preserve custom_files tracking)
        manifest.installed_packs.clear()
        self._save_manifest(manifest)

        logger.info("All rule packs reset, custom rules preserved")

    def create(self, pack_name: str, rules: list[dict]) -> str:
        """
        Create a custom pack from user-supplied rule definitions.
        Writes rules to .aegis/rules/<pack_name>/rules.yaml.
        Adds a 'custom' type entry to the manifest.
        Returns the pack directory path.
        """
        if not pack_name or not pack_name.replace("-", "").replace("_", "").isalnum():
            raise ValueError(
                "Pack name must contain only letters, digits, hyphens, and underscores"
            )

        manifest = self._load_manifest()
        if pack_name in manifest.installed_packs:
            raise ValueError(
                f"Pack '{pack_name}' already exists. "
                "Remove it first or use a different name."
            )

        self._ensure_rules_dir()
        pack_dir = os.path.join(self.rules_dir, pack_name)
        os.makedirs(pack_dir, exist_ok=True)

        rules_path = os.path.join(pack_dir, _RULES_FILE)
        with open(rules_path, "w", encoding="utf-8") as f:
            f.write(
                yaml.dump(
                    {"rules": rules}, default_flow_style=False, allow_unicode=True
                )
            )

        copied_files = [f"{pack_name}/{_RULES_FILE}"]

        # Write pack metadata file
        meta_path = os.path.join(pack_dir, _PACK_META_FILE)
        meta = RulePackMeta(
            name=pack_name,
            version="1.0.0",
            description=f"Custom rule pack: {pack_name}",
            author="User",
            pack_type="custom",
        )
        with open(meta_path, "w", encoding="utf-8") as f:
            f.write(yaml.dump(meta.model_dump(), default_flow_style=False))

        manifest.installed_packs[pack_name] = InstalledPack(
            name=pack_name,
            version="1.0.0",
            install_time=datetime.now(UTC).isoformat(),
            files=copied_files,
        )
        self._save_manifest(manifest)

        logger.info("Custom rule pack created", pack=pack_name, path=pack_dir)
        return pack_dir

    def install_defaults(self, pack_names: list[str] | None = None) -> list[str]:
        """
        Install the initial set of default packs for a fresh project.
        If pack_names is None, installs ALL available packs.
        Skips packs that are already installed (idempotent).
        Returns list of installed pack names.
        """
        available = self.list_available()
        if pack_names is None:
            pack_names = list(available.keys())

        installed: list[str] = []
        for name in pack_names:
            if name not in available:
                logger.warning("Unknown default pack, skipping", pack=name)
                continue
            if self.is_installed(name):
                continue
            try:
                self.install(name)
                installed.append(name)
            except Exception as exc:
                logger.error(
                    "Failed to install default pack", pack=name, error=str(exc)
                )

        return installed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_rules_dir(self) -> None:
        """Create .aegis/rules/ if it doesn't exist."""
        os.makedirs(self.rules_dir, exist_ok=True)

    def _load_manifest(self) -> PackManifest:
        """Deserialize .packs.json or return empty manifest."""
        path = os.path.join(self.rules_dir, _MANIFEST_FILE)
        if not os.path.isfile(path):
            return PackManifest()
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return PackManifest(**data)
        except Exception:
            logger.warning("Failed to read .packs.json, starting fresh")
            return PackManifest()

    def _save_manifest(self, manifest: PackManifest) -> None:
        """Serialize manifest to .packs.json."""
        self._ensure_rules_dir()
        path = os.path.join(self.rules_dir, _MANIFEST_FILE)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(manifest.model_dump(mode="json"), f, indent=2)
        except Exception as exc:
            logger.error("Failed to save .packs.json", error=str(exc))

    @staticmethod
    def _read_pack_meta(pack_resource_dir) -> RulePackMeta | None:
        """Read pack.yaml from a resource pack directory."""
        meta_file = pack_resource_dir.joinpath(_PACK_META_FILE)
        if not meta_file.is_file():
            return None
        try:
            with importlib.resources.as_file(meta_file) as path:
                with open(path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            if data and "name" in data:
                return RulePackMeta(**data)
        except Exception:
            pass
        return None

    def _has_local_changes(self, pack_name: str) -> bool:
        """
        Check whether any file in a pack directory
        differs from the shipped version.
        """
        pack_dir = os.path.join(self.rules_dir, pack_name)
        if not os.path.isdir(pack_dir):
            return False

        try:
            resource_root = importlib.resources.files(_PACKS_RESOURCE)
            pack_resource = resource_root.joinpath(pack_name)
        except Exception:
            return False

        for res_file in pack_resource.iterdir():
            if not res_file.is_file() or res_file.name == _PACK_META_FILE:
                continue
            dest = os.path.join(pack_dir, res_file.name)
            if not os.path.isfile(dest):
                return True
            try:
                with importlib.resources.as_file(res_file) as src_path:
                    with open(src_path, "rb") as sf:
                        src_content = sf.read()
                with open(dest, "rb") as df:
                    dest_content = df.read()
                if src_content != dest_content:
                    return True
            except Exception:
                return True

        return False
