import os
import json
from aegis.infrastructure.adapters.base import ToolAdapter, logger

class GenericMCPAdapter(ToolAdapter):
    """
    Fallback adapter for any tool following the standard MCP manifest pattern.
    Ensures that Aegis is discoverable by generic agentic ecosystems (including Gemini toolchains).
    """
    @property
    def name(self) -> str:
        return "Generic MCP"

    def is_available(self) -> bool:
        return True # Always available as a fallback

    def install(self) -> bool:
        # Standard MCP discovery file in project root
        manifest_path = self.target_dir / "mcp.json"
        
        manifest = {
            "mcpServers": {
                "aegis": {
                    "command": "uv",
                    "args": ["run", "aegis-kernel", "--transport", "stdio"],
                    "description": "Aegis Architectural Governance Engine"
                }
            }
        }

        try:
            if manifest_path.exists():
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "aegis" in data.get("mcpServers", {}):
                    return True
                # Merge into existing manifest
                if "mcpServers" not in data:
                    data["mcpServers"] = {}
                data["mcpServers"]["aegis"] = manifest["mcpServers"]["aegis"]
                manifest = data

            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
            return True
        except Exception as e:
            logger.error("Generic MCP manifest creation failed", error=str(e))
            return False
