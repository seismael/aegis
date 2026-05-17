import os
from aegis.infrastructure.adapters.base import ToolAdapter, logger

class OpenDevinAdapter(ToolAdapter):
    """
    Native integration for OpenDevin (often referred to as OpenCode).
    Registers Aegis as a trusted MCP server in the OpenDevin workspace configuration.
    """
    def is_available(self) -> bool:
        # Detect OpenDevin via environment or common config locations
        return os.path.exists(".opendevin") or os.environ.get("OPENDEVIN_BASE_URL") is not None

    def install(self) -> bool:
        # OpenDevin often uses a config.toml or .env for MCP
        config_path = self.target_dir / "config.toml"
        
        # We append the MCP definition to the project config
        directive = (
            '\n[[mcp_servers]]\n'
            'name = "aegis"\n'
            'command = "uv"\n'
            'args = ["run", "aegis-kernel", "--transport", "stdio"]\n'
        )
        
        try:
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if "aegis-kernel" in content:
                    return True
            
            with open(config_path, "a", encoding="utf-8") as f:
                f.write(directive)
            return True
        except Exception as e:
            logger.error("OpenDevin integration failed", error=str(e))
            return False
