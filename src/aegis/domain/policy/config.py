from pydantic import BaseModel


class AegisConfig(BaseModel):
    enforcement: str = "warn"
    phase_defaults: dict = {}
    category_overrides: dict = {}
    auto_baseline: bool = False
    max_violations: int = 1000
