from aegis.infrastructure.adapters.base import ToolAdapter


class AiderAdapter(ToolAdapter):
    """
    Native adapter for Aider.
    Configures Aider to use Aegis as an architect-mode MCP server.
    """

    @property
    def name(self) -> str:
        return "Aider"

    def is_present(self) -> bool:
        # Check if aider is in path
        import subprocess

        try:
            subprocess.run(["aider", "--version"], capture_output=True)
            return True
        except FileNotFoundError:
            return (self.home / ".aider.conf.yml").exists()

    def install(self) -> bool:
        config_path = self.home / ".aider.conf.yml"
        directive = "\nmcp-server: aegis-kernel --transport stdio\n"

        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                content = f.read()
            if "aegis-kernel" in content:
                return True

        with open(config_path, "a", encoding="utf-8") as f:
            f.write(directive)

        return True
