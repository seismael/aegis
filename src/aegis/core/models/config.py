"""Aegis project configuration models."""

from pydantic import BaseModel, Field


class AegisConfig(BaseModel):
    """Top-level Aegis project configuration loaded from .aegis/config.yaml."""

    enforcement: str = "warn"
    phase_defaults: dict[str, list[str]] | None = Field(
        default=None,
        description=(
            "Category-level phase overrides, "
            "e.g. {'security': ['ci', 'nightly']}"
        ),
    )
