"""
Aegis Universal Capability Installer.
Provides universal and native installation logic for all major AI agent coder tools.
"""

from typing import List, Optional
import structlog
from aegis.infrastructure.adapters.base import ToolAdapter
from aegis.infrastructure.adapters.claude import ClaudeAdapter
from aegis.infrastructure.adapters.aider import AiderAdapter
from aegis.infrastructure.adapters.opendevin import OpenDevinAdapter
from aegis.infrastructure.adapters.generic import GenericMCPAdapter

logger = structlog.get_logger()

class AegisInstaller:
    """
    Universal Capability Orchestrator.
    Binds Aegis as a native capability to all detected AI tools (Claude, Aider, OpenCode, Gemini, etc.).
    """
    def __init__(self, target_dir: str = "."):
        self.target_dir = target_dir
        self.adapters: List[ToolAdapter] = [
            ClaudeAdapter(target_dir),
            AiderAdapter(target_dir),
            OpenDevinAdapter(target_dir),
            GenericMCPAdapter(target_dir) # Catch-all standard
        ]

    def install_globally(self) -> None:
        """Installs the Aegis capability natively across all detected AI tools."""
        print(f"📦 Installing Aegis Universal Agentic Capability...")
        installed_count = 0
        
        for adapter in self.adapters:
            # We skip 'Generic' if specific tools are found, or keep it as a baseline
            if adapter.is_available():
                print(f"  ✓ Integrating with {adapter.__class__.__name__.replace('Adapter', '')}...")
                if adapter.install():
                    installed_count += 1

        if installed_count > 0:
            print("\n🛡️  Aegis Global Capability Setup Complete!")
            print("Your AI agents now natively possess the 'Aegis Governance' capability.")
        else:
            print("\n⚠️  No AI tools detected. Standard MCP manifest created for manual registration.")

    @staticmethod
    def entry_point():
        installer = AegisInstaller()
        installer.install_globally()
