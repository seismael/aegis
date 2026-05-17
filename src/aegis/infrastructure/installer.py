"""
Universal Installer for Aegis Architectural Governance.
Operates globally — binds MCP servers into AI tool configs and deploys agentic skills.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any

import structlog


logger = structlog.get_logger()


class UniversalInstaller:
    """
    Enterprise installation bootstrapper.
    Idempotently configures local AI coding environments to recognize
    the Aegis MCP server and registers the global agentic skills.

    Operates independently of any target repository.
    """

    def __init__(self):
        self.home = Path.home()
        self.claude_dir = self.home / ".claude"
        self.claude_config = self.claude_dir / "claude_desktop_config.json"
        self.claude_skills = self.claude_dir / "skills"

        self.aider_config = self.home / ".aider.conf.yml"

        # Source skills directory (within the installed package)
        pkg_root = Path(__file__).resolve().parent.parent.parent.parent
        self.skills_src = pkg_root / ".claude" / "skills"

    def execute_global_install(self) -> None:
        """Executes the full installation sequence across all detected tools."""
        self.logger = structlog.get_logger()
        self._ensure_directories()
        self._inject_claude_mcp()
        self._deploy_claude_skills()
        self._inject_aider_mcp()
        logger.info("Aegis Universal Installer completed successfully.")

    def _ensure_directories(self) -> None:
        self.claude_dir.mkdir(parents=True, exist_ok=True)
        self.claude_skills.mkdir(parents=True, exist_ok=True)

    def _inject_claude_mcp(self) -> None:
        """Mutates the global Claude Desktop / CLI configuration to bind Aegis."""
        config: Dict[str, Any] = {"mcpServers": {}}

        if self.claude_config.exists():
            try:
                with open(self.claude_config, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Corrupted Claude config detected. Creating backup.")
                backup = self.claude_config.with_suffix(".json.bak")
                self.claude_config.rename(backup)
                config = {"mcpServers": {}}

        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Idempotent: skip if already registered
        if "aegis" in config["mcpServers"]:
            logger.info("Aegis MCP server already registered in Claude config.")
            return

        config["mcpServers"]["aegis"] = {
            "command": "aegis",
            "args": ["run", "--transport", "stdio"],
        }

        with open(self.claude_config, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        logger.info("Claude MCP transport configuration updated.")

    def _inject_aider_mcp(self) -> None:
        """Appends the MCP server initialization to the global Aider configuration."""
        directive = "\nmcp-server: aegis run --transport stdio\n"

        if self.aider_config.exists():
            with open(self.aider_config, "r", encoding="utf-8") as f:
                content = f.read()
            if "aegis run" in content:
                logger.info("Aider MCP server already configured.")
                return

        with open(self.aider_config, "a", encoding="utf-8") as f:
            f.write(directive)

        logger.info("Aider MCP configuration updated.")

    def _deploy_claude_skills(self) -> None:
        """Copies agentic skills from the package to the global skills directory."""
        if not self.skills_src.exists() or not self.skills_src.is_dir():
            logger.warning("Skills source directory not found.", path=str(self.skills_src))
            return

        deployed = 0
        for item in self.skills_src.iterdir():
            if item.suffix == ".md":
                dest = self.claude_skills / item.name
                shutil.copy2(str(item), str(dest))
                deployed += 1

        logger.info("Agentic skills deployed.", count=deployed, target=str(self.claude_skills))
