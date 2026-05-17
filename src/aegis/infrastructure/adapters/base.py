from abc import ABC, abstractmethod
from pathlib import Path
import structlog

logger = structlog.get_logger()

class ToolAdapter(ABC):
    """
    Abstract base for AI tool-specific integration.
    Handles native plugin registration and configuration.
    """
    def __init__(self, target_dir: str):
        self.target_dir = Path(target_dir)
        self.home = Path.home()

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def is_present(self) -> bool:
        """Returns True if the tool is detected on the system."""
        pass

    @abstractmethod
    def install(self) -> bool:
        """Performs native installation of the Aegis capability."""
        pass

    def log_success(self):
        logger.info(f"Successfully installed Aegis capability into {self.name}")
