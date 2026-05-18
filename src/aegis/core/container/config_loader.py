"""Loads Aegis project configuration from .aegis/config.yaml."""

import os

import yaml

from aegis.core.models.config import AegisConfig


def load_aegis_config(root_dir: str) -> AegisConfig:
    """Load .aegis/config.yaml with phase override support.

    Returns default AegisConfig if the file does not exist or is invalid.
    """
    path = os.path.join(root_dir, ".aegis", "config.yaml")
    if not os.path.exists(path):
        return AegisConfig()
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return AegisConfig(**data)
    except Exception:
        return AegisConfig()
