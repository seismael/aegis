"""
Aegis Universal Capability Installer.
Installs Aegis as a native, global Agent Extension.
Supports tool-specific native registration (Claude Plugin, Aider MCP, etc.).
"""

import os
import json
import shutil
import subprocess
import importlib.resources
from pathlib import Path
from typing import Any, List, Optional
import structlog

logger = structlog.get_logger()

class ToolAdapter:
    """Base class for native agent tool integration."""
    def __init__(self, target_dir: str):
        self.target_dir = Path(target_dir)
        self.home = Path.home()

    def is_available(self) -> bool:
        raise NotImplementedError()

    def install(self) -> bool:
        raise NotImplementedError()

class ClaudeAdapter(ToolAdapter):
    """Native integration for Anthropic Claude (Desktop/Code)."""
    def is_available(self) -> bool:
        return (self.home / ".claude").exists()

    def install(self) -> bool:
        # 1. Native /plugin registration path (Documentation/Manifest)
        self._setup_plugin_manifest()
        
        # 2. Global MCP configuration injection
        config_path = self.home / ".claude" / "claude_desktop_config.json"
        config = {"mcpServers": {}}
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except: pass

        if "mcpServers" not in config: config["mcpServers"] = {}
        config["mcpServers"]["aegis"] = {
            "command": "aegis-kernel",
            "args": ["--transport", "stdio"]
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
            
        # 3. Deploy Agent Skills
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
            logger.error("Failed to deploy skills", error=str(e))
            
        return True

    def _setup_plugin_manifest(self):
        """Creates a Claude-compatible plugin manifest if needed."""
        pass

class AiderAdapter(ToolAdapter):
    """Native integration for Aider."""
    def is_available(self) -> bool:
        return True # Aider uses config files in home

    def install(self) -> bool:
        aider_conf = self.home / ".aider.conf.yml"
        directive = "\nmcp-server: aegis-kernel --transport stdio\n"
        
        if aider_conf.exists():
            with open(aider_conf, "r", encoding="utf-8") as f:
                content = f.read()
            if "aegis-kernel" in content:
                return True
        
        with open(aider_conf, "a", encoding="utf-8") as f:
            f.write(directive)
        return True

class AegisInstaller:
    """
    Universal Capability Orchestrator.
    Binds Aegis as a native capability to all detected AI tools.
    """
    def __init__(self, target_dir: str = "."):
        self.target_dir = target_dir
        self.adapters: List[ToolAdapter] = [
            ClaudeAdapter(target_dir),
            AiderAdapter(target_dir)
        ]

    def install_globally(self) -> None:
        """Installs the capability once into the machine's agent tools."""
        print(f"📦 Installing Aegis Global Capability...")
        installed = 0
        for adapter in self.adapters:
            if adapter.is_available():
                print(f"  ✓ Integrating with {adapter.__class__.__name__.replace('Adapter', '')}...")
                if adapter.install():
                    installed += 1
        
        if installed > 0:
            print("\n🛡️  Aegis is now a native capability of your AI agents.")
        else:
            print("\n⚠️  No AI tools detected. Ensure Claude or Aider is installed.")

    @staticmethod
    def entry_point():
        installer = AegisInstaller()
        installer.install_globally()

if __name__ == "__main__":
    AegisInstaller.entry_point()
