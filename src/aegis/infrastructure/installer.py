"""
Aegis Capability Installer.
Installs Aegis as a global agent capability (Extension/Plugin).
Binds MCP servers and deploys agentic skills to the user's AI tools.
"""

import importlib.resources
import json
import shutil
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger()


class AegisInstaller:
    """
    Global Agent Capability Installer.
    Introduces the 'Aegis Governance' capability to Claude, Aider, and other tools.
    This is run ONCE per machine to register the engine globally.
    """

    def __init__(self):
        self.home = Path.home()
        # Claude Desktop / Code configuration
        self.claude_dir = self.home / ".claude"
        self.claude_config = self.claude_dir / "claude_desktop_config.json"
        self.claude_skills = self.claude_dir / "skills"

        # Aider configuration
        self.aider_config = self.home / ".aider.conf.yml"

    def install_global_capability(self) -> None:
        """
        Executes the global installation sequence.
        Makes the Aegis capability available to all AI agents on the system.
        """
        self._ensure_directories()
        self._inject_claude_capability()
        self._deploy_agent_skills()
        self._inject_aider_capability()
        logger.info("Aegis Global Capability installed successfully.")

    def _ensure_directories(self) -> None:
        """Ensures that global agent configuration directories exist."""
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        self.claude_skills.mkdir(parents=True, exist_ok=True)

    def _inject_claude_capability(self) -> None:
        """Registers Aegis as a global MCP capability for Claude."""
        config: dict[str, Any] = {"mcpServers": {}}

        if self.claude_config.exists():
            try:
                with open(self.claude_config, encoding="utf-8") as f:
                    config = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Claude config corrupted. Creating backup.")
                backup = self.claude_config.with_suffix(".json.bak")
                if backup.exists():
                    backup.unlink()
                self.claude_config.rename(backup)
                config = {"mcpServers": {}}

        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Idempotent registration
        config["mcpServers"]["aegis"] = {
            "command": "aegis-kernel",  # Use the console script
            "args": ["--transport", "stdio"],
        }

        with open(self.claude_config, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logger.info("Claude capability registered.")

    def _inject_aider_capability(self) -> None:
        """Registers Aegis as a global MCP capability for Aider."""
        # Use .aider.conf.yml in the home directory for global availability
        directive = "\nmcp-server: aegis-kernel --transport stdio\n"

        if self.aider_config.exists():
            with open(self.aider_config, encoding="utf-8") as f:
                content = f.read()
            if "aegis-kernel" in content:
                return

        with open(self.aider_config, "a", encoding="utf-8") as f:
            f.write(directive)
        logger.info("Aider capability registered.")

    def _deploy_agent_skills(self) -> None:
        """Deploys the AI instruction skills to the global agent store."""
        deployed = 0
        try:
            # Load skills from the package resources
            traversable = importlib.resources.files("aegis.resources.skills")
            for item in traversable.iterdir():
                if item.name.endswith(".md"):
                    dest = self.claude_skills / item.name
                    with importlib.resources.as_file(item) as skill_file:
                        shutil.copy2(str(skill_file), str(dest))
                    deployed += 1
            logger.info("Agent skills deployed.", count=deployed)
        except Exception as e:
            logger.error("Failed to deploy skills.", error=str(e))

    @staticmethod
    def entry_point():
        installer = AegisInstaller()
        installer.install_global_capability()
        print("\n[Aegis] Global Capability Installed!")
        print(
            "Your AI agents (Claude, Aider, etc.) now have the 'Aegis Governance' capability."
        )
        print(
            "To apply governance to a specific project, enter the directory and run: `aegis init`."
        )
