"""Aegis project configuration models."""

from pydantic import BaseModel, Field


class AegisConfig(BaseModel):
    """Top-level Aegis project configuration loaded from .aegis/config.yaml."""

    enforcement: str = "warn"
    phase_defaults: dict[str, list[str]] | None = Field(
        default=None,
        description=(
            "Category-level phase overrides, e.g. {'security': ['ci', 'nightly']}"
        ),
    )
    category_overrides: dict[str, list[str]] | None = Field(
        default=None,
        description=(
            "Per-category phase assignment applied after phase_defaults,"
            " e.g. {'style': ['pre-commit']}"
        ),
    )
    auto_baseline: bool = Field(
        default=False,
        description=(
            "Automatically capture all violations into the baseline"
            " on each check invocation"
        ),
    )
    max_violations: int = Field(
        default=0,
        description=(
            "Warn when active violations exceed this threshold."
            " 0 = no limit."
        ),
    )
