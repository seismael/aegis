import logging
import os

import typer


class AegisCLI:
    """
    Headless CLI for Aegis V4 Agent-Native Microkernel.
    Two commands: install (global agent config) and run (MCP server).
    No human-facing output — agents handle everything via MCP.
    """

    def __init__(self):
        self.app = typer.Typer(help="Aegis V4: Agent-Native Architectural Microkernel")
        self.app.command()(self.init)
        self.app.command()(self.run)
        self.app.command()(self.agent)

    def init(
        self,
        workspace_root: str = typer.Option(
            ".", "--workspace", help="Path to the workspace root"
        ),
        tool: str | None = typer.Option(
            None, "--tool", help="Target tool: claude, aider, gemini (omit for all)"
        ),
    ):
        """Initialize Aegis in the local workspace by creating local agent config overrides."""
        from aegis.infrastructure.installer import AgentNativeInstaller

        installer = AgentNativeInstaller()
        try:
            installer.init_workspace(workspace_root=workspace_root, target_tool=tool)
        except Exception as e:
            typer.echo(f"ERROR: {e}", err=True)
            raise typer.Exit(code=1) from None

    def run(
        self,
        transport: str = typer.Option(
            "stdio", "--transport", help="MCP transport: stdio, sse, streamable-http"
        ),
        host: str = typer.Option("127.0.0.1", "--host", help="Bind host (SSE/HTTP)"),
        port: int = typer.Option(8000, "--port", help="Bind port (SSE/HTTP)"),
        headless_check: bool = typer.Option(
            False,
            "--headless-check",
            help="Run a single compliance check and exit (for CI/Aider test-cmd)",
        ),
    ):
        """Start the headless Aegis MCP microkernel server."""
        from aegis.kernel.server import AegisKernel

        kernel = AegisKernel()
        if headless_check:
            violations = kernel.run_headless_check()
            if violations > 0:
                raise typer.Exit(code=1)
            raise typer.Exit(code=0)

        kernel.run(transport=transport, host=host, port=port)

    def agent(
        self,
        workspace_root: str = typer.Option(
            ".", "--workspace", help="Path to workspace root"
        ),
        plan_import: str | None = typer.Option(
            None, "--plan-import", help="Proposed import to verify"
        ),
        target_module: str | None = typer.Option(
            None, "--target-module", help="Target module name"
        ),
    ):
        """Execute AegisAgent native runtime proactive plan verification."""
        from aegis.kernel.server import AegisKernel

        kernel = AegisKernel(workspace_root=workspace_root)
        if plan_import and target_module:
            res = kernel.agent.verify_plan([plan_import], target_module)
            typer.echo(f"Plan valid: {res['plan_valid']}")
            typer.echo(res["feedback"])
            if not res["plan_valid"]:
                raise typer.Exit(code=1)
        else:
            typer.echo(f"AegisAgent native runtime active in {kernel.workspace_root}")

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
