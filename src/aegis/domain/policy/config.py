from pydantic import BaseModel


class AegisConfig(BaseModel):
    enforcement: str = "block"
    phase_defaults: dict = {}
    category_overrides: dict = {}
    auto_baseline: bool = False
    max_violations: int = 1000

    @classmethod
    def parse_yaml(cls, path: str) -> "AegisConfig":
        import os

        import yaml

        if not os.path.exists(path):
            return cls()
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        except Exception:
            return cls()
