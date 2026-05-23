import logging
import os
import sys

import typer


class AegisCLI:
    """
    Headless CLI for Aegis V4 Agent-Native Microkernel.
    Two commands only: install (global agent config injection) and run (start MCP server).
    No human-facing output during development — agents handle everything via MCP.
    """

    def __init__(self):
        self.app = typer.Typer(help="Aegis V4: Agent-Native Architectural Microkernel")
        self.app.command()(self.install)
        self.app.command()(self.run)

    def install(
        self,
        tool: str | None = typer.Option(
            None, "--tool", help="Target tool: claude, aider (omit for all)"
        ),
    ):
        """Inject Aegis MCP server config and cognitive directives into Claude/Aider."""
        from aegis.infrastructure.installer import AgentNativeInstaller

        installer = AgentNativeInstaller()
        installer.install(target_tool=tool)

    def run(
        self,
        transport: str = typer.Option(
            "stdio", "--transport", help="MCP transport: stdio, sse, streamable-http"
        ),
        host: str = typer.Option("127.0.0.1", "--host", help="Bind host (SSE/HTTP)"),
        port: int = typer.Option(8000, "--port", help="Bind port (SSE/HTTP)"),
    ):
        """Start the headless Aegis MCP microkernel server."""
        from aegis.kernel.server import AegisKernel

        kernel = AegisKernel()
        kernel.run(transport=transport, host=host, port=port)

    @staticmethod
    def entry_point():
        logging.basicConfig(
            level=logging.WARNING
            if "AEGIS_VERBOSE" not in os.environ
            else logging.DEBUG,
        )
        cli = AegisCLI()
        cli.app()


if __name__ == "__main__":
    AegisCLI.entry_point()
