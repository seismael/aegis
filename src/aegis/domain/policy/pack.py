"""Rule pack data models — versioned, named collections of governance rules."""

from pydantic import BaseModel, Field


class RulePackMeta(BaseModel):
    """Metadata descriptor for a rule pack (no rules embedded)."""

    name: str
    version: str
    description: str
    author: str = "Aegis"
    pack_type: str = "default"  # "default" | "custom"
    source: str | None = None  # resource path or file path
    default_phases: list[str] | None = None  # pack-level phase defaults


class InstalledPack(BaseModel):
    """Entry in the installed-packs manifest."""

    name: str
    version: str
    install_time: str  # ISO 8601
    files: list[str] = Field(default_factory=list)  # relative paths from .aegis/rules/
    custom_overrides: list[str] = Field(
        default_factory=list
    )  # rule IDs the user edited locally


class PackManifest(BaseModel):
    """Contents of .aegis/rules/.packs.json."""

    installed_packs: dict[str, InstalledPack] = Field(default_factory=dict)
    custom_files: list[str] = Field(default_factory=list)
    version: int = 1  # schema version for future migration
