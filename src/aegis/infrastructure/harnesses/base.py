from abc import ABC, abstractmethod
from pathlib import Path

class BaseHarness(ABC):
    def __init__(self, home: Path):
        self.home = home

    @abstractmethod
    def install(self) -> list[str]:
        """Inject Aegis into the harness global config. Returns list of error messages."""
        pass

    @abstractmethod
    def deploy_skills(self) -> list[str]:
        """Deploy markdown skills to the harness global registry."""
        pass

    @abstractmethod
    def deploy_workspace_instructions(self, workspace_root: str) -> list[str]:
        """Generate/update workspace-level instructions (GEMINI.md, .claude.md, etc.)"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
