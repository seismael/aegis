import shutil

from aegis.infrastructure.adapters.base import ToolAdapter


class AiderAdapter(ToolAdapter):
    """
    Native adapter for Aider.
    Configures Aider to use Aegis as an architect-mode MCP server.
    """

    def __init__(self, target_dir: str, home_dir: str | None = None):
        super().__init__(target_dir, home_dir)

    @property
    def name(self) -> str:
        return "Aider"

    def is_present(self) -> bool:
        # Check if aider is in path
        if shutil.which("aider"):
            return True
        return (self.home / ".aider.conf.yml").exists()

    def install(self, sandbox: bool = False) -> bool:  # noqa: ARG002
        config_path = self.home / ".aider.conf.yml"

        try:
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    content = f.read()
                if "aegis-kernel" in content:
                    return True
                # Append with leading newline to separate from existing content
                with open(config_path, "a", encoding="utf-8") as f:
                    f.write("\nmcp-server: aegis-kernel --transport stdio\n")
            else:
                config_path.write_text(
                    "mcp-server: aegis-kernel --transport stdio\n", encoding="utf-8"
                )

            return True
        except OSError:
            return False

    def uninstall(self) -> bool:
        config_path = self.home / ".aider.conf.yml"
        if not config_path.exists():
            return True
        try:
            with open(config_path, encoding="utf-8") as f:
                lines = f.readlines()
            lines = [line for line in lines if "aegis-kernel" not in line]
            with open(config_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return True
        except OSError:
            return False
