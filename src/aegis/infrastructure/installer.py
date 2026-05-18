"""
Aegis Universal Capability Installer.
Provides universal and native installation logic for all major AI agent coder tools.
"""

import structlog

from aegis.infrastructure.adapters.aider import AiderAdapter
from aegis.infrastructure.adapters.base import ToolAdapter
from aegis.infrastructure.adapters.claude import ClaudeAdapter
from aegis.infrastructure.adapters.generic import GenericMCPAdapter
from aegis.infrastructure.adapters.opendevin import OpenDevinAdapter

logger = structlog.get_logger()


class AegisInstaller:
    """
    Universal Capability Orchestrator.
    Binds Aegis as a native capability to all detected AI tools
    (Claude, Aider, OpenCode, Gemini, etc.).
    """

    def __init__(self, target_dir: str = "."):
        self.target_dir = target_dir
        self.adapters: list[ToolAdapter] = [
            ClaudeAdapter(target_dir),
            AiderAdapter(target_dir),
            OpenDevinAdapter(target_dir),
            GenericMCPAdapter(target_dir),  # Catch-all standard
        ]

    def install_global_capability(self, target_tool: str | None = None) -> None:
        """Installs the Aegis capability natively across all detected AI tools."""
        print("📦 Installing Aegis Universal Capability...")
        to_install = self.adapters
        if target_tool:
            to_install = [
                a for a in self.adapters if target_tool.lower() in a.name.lower()
            ]
            if not to_install:
                print(f"❌ Error: Tool '{target_tool}' not supported or not found.")
                return

        installed_count = 0

        for adapter in to_install:
            if adapter.is_present() or target_tool:
                print(f"  ✓ Integrating with {adapter.name}...")
                if adapter.install():
                    installed_count += 1

        if installed_count > 0:
            print("\n🛡️  Aegis Global Capability Setup Complete!")
            print(
                "Your AI agents now natively possess the 'Aegis Governance' capability."
            )
        else:
            print(
                "\n⚠️  No AI tools detected."
                " Standard MCP manifest for manual registration."
            )

    @staticmethod
    def entry_point():
        installer = AegisInstaller()
        installer.install_global_capability()
