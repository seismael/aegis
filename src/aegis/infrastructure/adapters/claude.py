import os
import json
import shutil
import subprocess
import importlib.resources
from aegis.infrastructure.adapters.base import AgentAdapter, logger

class ClaudeAdapter(AgentAdapter):
    """
    Native adapter for Anthropic Claude (Desktop and CLI).
    Prioritizes official /plugin installation where supported.
    """
    @property
    def name(self) -> str:
        return "Claude"

    def is_present(self) -> bool:
        claude_paths = [
            self.home / ".claude",
            Path(os.environ.get("APPDATA", "")) / "Claude",
        ]
        return any(p.exists() for p in claude_paths)

    def install(self) -> bool:
        # 1. Try native 'claude' CLI registration if available
        if self._try_native_mcp_add():
            return True
            
        # 2. Fallback to raw config mutation (Robust Default)
        self._manual_config_injection()
        self._deploy_skills()
        return True

    def _try_native_mcp_add(self) -> bool:
        """Attempts to use the 'claude' CLI to add the MCP server."""
        try:
            # Future-proofing for when 'claude mcp add' or similar exists
            # For now, we'll check if the command exists
            result = subprocess.run(["claude", "mcp", "add", "aegis", "--command", "aegis-kernel"], 
                                    capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _manual_config_injection(self) -> None:
        config_path = self.home / ".claude" / "claude_desktop_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        config = {"mcpServers": {}}
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except json.JSONDecodeError:
                pass

        if "mcpServers" not in config:
            config["mcpServers"] = {}

        config["mcpServers"]["aegis"] = {
            "command": "aegis-kernel",
            "args": ["--transport", "stdio"]
        }

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def _deploy_skills(self) -> None:
        skills_dest = self.home / ".claude" / "skills"
        skills_dest.mkdir(parents=True, exist_ok=True)
        
        try:
            traversable = importlib.resources.files("aegis.resources.skills")
            for item in traversable.iterdir():
                if item.name.endswith(".md"):
                    dest = skills_dest / item.name
                    with importlib.resources.as_file(item) as skill_file:
                        shutil.copy2(str(skill_file), str(dest))
        except Exception as e:
            logger.warning("Skill deployment failed", error=str(e))
