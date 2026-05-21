import importlib.resources
import json
import os
import shutil
import subprocess
from pathlib import Path

from aegis.infrastructure.adapters.base import ToolAdapter, logger


class ClaudeAdapter(ToolAdapter):
    """
    Native adapter for Anthropic Claude (Desktop and CLI).
    Prioritizes official CLI-based installation where available.
    """

    @property
    def name(self) -> str:
        return "Claude"

    def is_present(self) -> bool:
        # Check for existing Claude directories
        claude_paths = [
            self.home / ".claude",
            Path(os.environ.get("APPDATA", "")) / "Claude",
        ]
        if any(p.exists() for p in claude_paths):
            return True
        # Also check for claude CLI on PATH (Claude Code)
        try:
            subprocess.run(["claude", "--version"], capture_output=True, check=False)
            return True
        except FileNotFoundError:
            return False

    def install(self, sandbox: bool = False) -> bool:
        # 1. Try native 'claude' CLI registration (The Preferred Native Method)
        if self._try_native_mcp_add(sandbox=sandbox):
            self._deploy_skills()
            return True

        # 2. Fallback to raw config mutation (Robust Default)
        self._manual_config_injection(sandbox=sandbox)
        self._deploy_skills()
        return True

    def uninstall(self) -> bool:
        """Removes Aegis from Claude config and skills."""
        if self._try_native_mcp_remove():
            self._remove_skills()
            return True
        self._manual_config_removal()
        self._remove_skills()
        return True

    def _try_native_mcp_add(self, sandbox: bool = False) -> bool:
        """Attempts to use the 'claude' CLI to add the MCP server natively."""
        try:
            # Command: claude mcp add [name] [command] [args...]
            # This is the 'Native Plugin' installation method for Claude Code
            args = ["aegis-kernel", "--", "--transport", "stdio"]
            if sandbox:
                args.append("--sandbox")

            result = subprocess.run(
                ["claude", "mcp", "add", "aegis"] + args,
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _try_native_mcp_remove(self) -> bool:
        """Attempts to use the 'claude' CLI to remove the MCP server."""
        try:
            result = subprocess.run(
                ["claude", "mcp", "remove", "aegis"],
                capture_output=True,
                text=True,
                check=False,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _manual_config_injection(self, sandbox: bool = False) -> None:
        """Fallback: Directly mutate the Claude Desktop configuration JSON."""
        config_path = self.home / ".claude" / "claude_desktop_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config = {"mcpServers": {}}
        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    config = json.load(f)
            except json.JSONDecodeError:
                pass

        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # The Hostage Maneuver: If in sandbox mode, disable standard filesystem
        if sandbox:
            if "filesystem" in config["mcpServers"]:
                # Prefix with disabled_ to unregister from Claude but keep config
                config["mcpServers"]["disabled_filesystem"] = config["mcpServers"].pop(
                    "filesystem"
                )
                logger.info("Sandbox Mode: Standard filesystem server disabled.")

        config["mcpServers"]["aegis"] = {
            "command": "aegis-kernel",
            "args": ["--transport", "stdio"] + (["--sandbox"] if sandbox else []),
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def _manual_config_removal(self) -> None:
        """Removes Aegis entry from Claude Desktop configuration JSON."""
        config_path = self.home / ".claude" / "claude_desktop_config.json"
        if not config_path.exists():
            return
        try:
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
            config.get("mcpServers", {}).pop("aegis", None)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except (json.JSONDecodeError, OSError):
            pass

    def _deploy_skills(self) -> None:
        """Deploys AI instruction skills to Claude's native skills directory."""
        skills_dest = self.home / ".claude" / "skills"
        skills_dest.mkdir(parents=True, exist_ok=True)

        try:
            traversable = importlib.resources.files("aegis.resources.skills")
            for item in traversable.iterdir():
                if item.name.endswith(".md"):
                    dest = skills_dest / item.name
                    shutil.copy2(str(item), str(dest))
        except Exception as e:
            logger.warning("Skill deployment failed", error=str(e))

    def _remove_skills(self) -> None:
        """Removes deployed Aegis skill files from Claude's skills directory."""
        skills_dest = self.home / ".claude" / "skills"
        if not skills_dest.exists():
            return
        try:
            traversable = importlib.resources.files("aegis.resources.skills")
            for item in traversable.iterdir():
                if item.name.endswith(".md"):
                    dest = skills_dest / item.name
                    dest.unlink(missing_ok=True)
        except Exception as e:
            logger.warning("Skill removal failed", error=str(e))
