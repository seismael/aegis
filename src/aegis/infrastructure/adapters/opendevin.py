import os

from aegis.infrastructure.adapters.base import ToolAdapter, logger


class OpenDevinAdapter(ToolAdapter):
    """
    Native integration for OpenDevin (often referred to as OpenCode).
    Registers Aegis as a trusted MCP server in the OpenDevin workspace configuration.
    """

    @property
    def name(self) -> str:
        return "OpenDevin"

    @property
    def aliases(self) -> list[str]:
        return ["opencode"]

    def is_present(self) -> bool:
        # Detect OpenDevin via environment or common config locations
        return (
            os.path.exists(".opendevin")
            or os.environ.get("OPENDEVIN_BASE_URL") is not None
        )

    def install(self, sandbox: bool = False) -> bool:  # noqa: ARG002
        # OpenDevin often uses a config.toml or .env for MCP
        config_path = self.target_dir / "config.toml"

        # We append the MCP definition to the project config
        directive = (
            "\n[[mcp_servers]]\n"
            'name = "aegis"\n'
            'command = "uv"\n'
            'args = ["run", "aegis-kernel", "--transport", "stdio"]\n'
        )

        try:
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    content = f.read()
                if "aegis-kernel" in content:
                    return True

            with open(config_path, "a", encoding="utf-8") as f:
                f.write(directive)
            return True
        except Exception as e:
            logger.error("OpenDevin integration failed", error=str(e))
            return False

    def uninstall(self) -> bool:
        config_path = self.target_dir / "config.toml"
        if not config_path.exists():
            return True
        try:
            with open(config_path, encoding="utf-8") as f:
                content = f.read()
            # Remove the [[mcp_servers]] block for aegis
            lines = content.splitlines(keepends=True)
            filtered = []
            in_block = False
            drop_block = False
            for line in lines:
                if line.strip().startswith("[[mcp_servers]]"):
                    if in_block and drop_block:
                        drop_block = False
                    in_block = True
                    drop_block = False
                if in_block and 'name = "aegis"' in line:
                    drop_block = True
                    continue
                if not in_block or not drop_block:
                    filtered.append(line)
                if in_block and line.strip() == "":
                    in_block = False
                    drop_block = False
            with open(config_path, "w", encoding="utf-8") as f:
                f.writelines(filtered)
            return True
        except OSError:
            return False
