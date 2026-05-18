import json
import logging
import os
from collections import Counter

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

from aegis.core.container.app import Container
from aegis.core.models.evolution import EvolutionDecision
from aegis.domain.governance.service import GovernanceService
from aegis.domain.policy.models import EnforcementMode


class AegisCLI:
    """
    Headless CLI for Aegis.
    Focused on CI/CD pipelines, environment bootstrapping, and diagnostic auditing.
    """

    def __init__(self, container: Container | None = None):
        self.container = container or Container()
        self.console = Console()
        self.app = typer.Typer(help="Aegis: Headless Architectural Governance Engine")
        self._register_commands()

    def _require_governance(self) -> None:
        """Exit with error if governance service is unavailable."""
        if not self.container.governance_service:
            self.console.print(
                "[red]Error: Governance service unavailable"
                " — container running in degraded mode."
                " Check .aegis/ permissions or run 'aegis init'.[/red]"
            )
            raise typer.Exit(code=1)

    def _register_commands(self):
        self.app.command()(self.install)
        self.app.command()(self.init)
        self.app.command()(self.check)
        self.app.command()(self.baseline)
        self.app.command()(self.status)
        self.app.command()(self.apply)
        self.app.command()(self.evolve)
        self.app.command()(self.setup_hooks)
        self.app.command()(self.serve)
        self.app.command()(self.self_check)

    def install(
        self,
        tool: str | None = typer.Argument(
            None, help="Specific tool to install into (e.g. claude, aider)"
        ),
    ):
        """Globally installs Aegis MCP configs and AI Skills into agent tools."""
        from aegis.infrastructure.installer import AegisInstaller

        self.console.print(
            "[bold blue]Executing Aegis Installation for"
            f" {tool or 'all tools'}...[/bold blue]"
        )
        try:
            installer = AegisInstaller()
            installer.install_global_capability(target_tool=tool)
        except Exception as e:
            self.console.print(f"[bold red]Installation failed:[/bold red] {str(e)}")
            raise typer.Exit(code=1) from e

    def init(self):
        """
        Initializes Aegis governance for the CURRENT project.
        Sets up the .aegis/ directory with modular rule packs and base configuration.
        """
        aegis_dir = GovernanceService.init_project_structure(
            self.container.workspace_root
        )
        self.console.print(f"[green]Initialized .aegis/ at {aegis_dir}[/green]")
        self.console.print("\n[bold green]Project Governance Initialized![/bold green]")
        self.console.print(
            "Optional: Run `aegis setup-hooks`"
            " to enable local Git pre-commit enforcement."
        )
        self.console.print(
            "Run `/aegis-init` in your AI chat to begin architectural discovery."
        )

    def check(
        self,
        staged: bool = typer.Option(
            False, "--staged", help="Check only staged changes"
        ),
        rule: str | None = typer.Option(
            None, "--rule", help="Filter by specific rule ID"
        ),
        strict: bool = typer.Option(
            False, "--strict", help="Treat warnings/reports as blocking"
        ),
    ):
        """Performs a gated compliance check. Non-zero exit on blocking violations."""
        all_rules = self.container.load_rules()
        if not all_rules:
            self.console.print(
                "[red]Error: No rules found in .aegis/rules/."
                " Run 'aegis init' first.[/red]"
            )
            raise typer.Exit(code=1)

        rules = [r for r in all_rules if r.id == rule] if rule else all_rules
        rule_map = {r.id: r for r in rules}

        if staged:
            if not self.container.evaluation_service:
                self.console.print(
                    "[red]Error: Evaluation service unavailable"
                    " — container running in degraded mode.[/red]"
                )
                raise typer.Exit(code=1)
            violations = self.container.evaluation_service.evaluate_changes(
                rules, root_dir=self.container.workspace_root
            )
            bm = self.container.baseline_manager or (
                self.console.print(
                    "[yellow]Warning: Baseline manager unavailable —"
                    " skipping exemption check.[/yellow]"
                )
                or None
            )
            active = (
                [v for v in violations if not bm.is_exempt(v, rule_map.get(v.rule_id))]
                if bm
                else violations
            )
        else:
            self._require_governance()
            active = self.container.governance_service.get_active_violations(
                rules, self.container.workspace_root
            )

        if not active:
            self.console.print("[green]Architecture compliant.[/green]")
            return

        # Blocking logic
        blocking_modes = {EnforcementMode.BLOCK}
        if strict:
            blocking_modes.add(EnforcementMode.WARN)
            blocking_modes.add(EnforcementMode.REPORT)

        blocking = []
        for v in active:
            r_obj = rule_map.get(v.rule_id)
            if r_obj and r_obj.mode in blocking_modes:
                blocking.append(v)

        for v in active:
            r_obj = rule_map.get(v.rule_id)
            mode = (
                r_obj.mode.value if r_obj else "warn"
            )  # Default to warn for unknown rules
            style = "red" if mode == "block" else "yellow"
            self.console.print(
                f"- [{style}]{mode.upper()}[/{style}] {v.file}:{v.line} ({v.rule_id})"
            )

        if blocking:
            self.console.print(
                "\n[bold red]Blocked:"
                f" {len(blocking)} architectural violations detected.[/bold red]"
            )
            raise typer.Exit(code=1)

    def baseline(
        self,
        clear: bool = typer.Option(
            False, "--clear", help="Clear the existing baseline"
        ),
    ):
        """Manages the architectural technical debt ledger."""
        if clear:
            bm = self.container.baseline_manager
            if not bm:
                self.console.print(
                    "[red]Error: Baseline manager unavailable"
                    " — container running in degraded mode.[/red]"
                )
                return
            if os.path.exists(bm.path):
                os.remove(bm.path)
            self.console.print("[yellow]Baseline cleared.[/yellow]")
            return

        self._require_governance()
        rules = self.container.load_rules()
        if not rules:
            self.console.print("[red]Error: No rules found in .aegis/rules/.[/red]")
            return

        count = self.container.governance_service.capture_baseline(
            rules, self.container.workspace_root
        )
        self.console.print(f"[green]Successfully baselined {count} violations.[/green]")

    def status(self, json_output: bool = typer.Option(False, "--json")):
        """Provides a summary of the current governance state."""
        rules = self.container.load_rules()
        baseline = (
            self.container.baseline_manager.load_baseline_raw()
            if self.container.baseline_manager
            else []
        )

        # Engine distribution
        engine_counts = Counter(r.engine_type.value for r in rules)

        # Active violations (run evaluation, subtract baseline)
        active_violations = []
        if rules and self.container.governance_service:
            active_violations = self.container.governance_service.get_active_violations(
                rules, self.container.workspace_root
            )

        stats = {
            "rules_count": len(rules),
            "baseline_violations": len(baseline),
            "active_violations": len(active_violations),
            "engines": dict(engine_counts),
            "plugins": list(self.container.loaded_plugins),
            "project_root": self.container.workspace_root,
        }

        if json_output:
            # Enums to values for JSON
            full_stats = stats.copy()
            full_stats["rules"] = [
                {
                    "id": r.id,
                    "description": r.description,
                    "severity": r.severity.value,
                    "mode": r.mode.value,
                    "language": r.language,
                    "active_violations": len(
                        [v for v in active_violations if v.rule_id == r.id]
                    ),
                    "baseline_entries": len(
                        [b for b in baseline if b.get("rule_id") == r.id]
                    ),
                }
                for r in rules
            ]
            print(json.dumps(full_stats, indent=2))
        else:
            self.console.print(
                f"Aegis Status: {len(rules)} rules, {len(baseline)} legacy debt items."
            )

    def apply(
        self,
        rule: str | None = typer.Option(
            None, "--rule", help="Specific rule to remediate"
        ),
        output: str | None = typer.Option(
            None, "--output", help="Write remediation prompt to file"
        ),
    ):
        """Displays remediation prompts for active violations."""
        self.console.print(
            "[bold blue]Aegis Architectural Remediation Audit[/bold blue]"
        )

        all_rules = self.container.load_rules()
        if not all_rules:
            self.console.print("[red]Error: No rules found in .aegis/rules/.[/red]")
            return

        rules = [r for r in all_rules if r.id == rule] if rule else all_rules
        rule_map = {r.id: r for r in rules}

        self._require_governance()
        active = self.container.governance_service.get_active_violations(
            rules, self.container.workspace_root
        )

        if not active:
            self.console.print(
                "[green]No active violations found for remediation.[/green]"
            )
            return
        prompt = self.container.remediation_synthesizer.generate_remediation(
            active, rule_map
        )

        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(prompt)
            self.console.print(f"[green]Remediation prompt written to {output}[/green]")
        else:
            self.console.print(prompt)

    def evolve(
        self, rule_id: str = typer.Argument(..., help="The ID of the rule to evolve")
    ):
        """Consensus recording flow for rule modifications."""
        self.console.print(
            f"[bold blue]Aegis Architectural Evolution: {rule_id}[/bold blue]"
        )

        rules = self.container.load_rules()
        if not rules:
            self.console.print("[red]Error: No rules found in .aegis/rules/.[/red]")
            return

        rule = next((r for r in rules if r.id == rule_id), None)

        if not rule:
            self.console.print(f"[red]Error: Rule '{rule_id}' not found.[/red]")
            return

        action = Prompt.ask(
            "Consensus Action?",
            choices=["suppress", "relax_rule", "refactor_required"],
            default="suppress",
        )
        rationale = Prompt.ask("Decision Rationale")

        decision = EvolutionDecision(
            rule_id=rule_id, action=action, rationale=rationale
        )
        if self.container.evolution_service:
            self.container.evolution_service.log_decision(decision)
        else:
            self.console.print(
                "[red]Error: Evolution service unavailable"
                " — decision not recorded.[/red]"
            )
            return

        if action == "suppress":
            self._require_governance()
            self.console.print(
                "[yellow]Capturing current violations"
                " for this rule into baseline...[/yellow]"
            )
            violation_count = self.container.governance_service.capture_baseline(
                [rule], self.container.workspace_root
            )
            self.console.print(
                f"[green]Successfully suppressed {violation_count} violations.[/green]"
            )

        self.console.print("\n✅ Decision recorded in evolution_log.json")

    def setup_hooks(self):
        """Demonstrates how to wire Aegis into Git hooks as an optional capability."""
        self.console.print("[bold blue]Aegis Git Hook Integration[/bold blue]")

        git_dir = os.path.join(self.container.workspace_root, ".git")
        if not os.path.exists(git_dir):
            self.console.print("[yellow]Skipping: Not a Git repository.[/yellow]")
            return

        hook_path = os.path.join(git_dir, "hooks", "pre-commit")

        # Professional Example Hook Content
        hook_content = (
            "#!/bin/sh\n"
            "# Aegis Pre-Commit Enforcement (Example)\n"
            "# This hook ensures architectural compliance before every commit.\n"
            "\n"
            'echo "🛡️  Aegis: Validating architectural compliance..."\n'
            "aegis check --staged\n"
            "\n"
            "if [ $? -ne 0 ]; then\n"
            '  echo "❌  Architectural drift detected. Commit blocked."\n'
            "  exit 1\n"
            "fi\n"
        )

        if os.path.exists(hook_path):
            if not Confirm.ask(
                f"Hook already exists at {hook_path}. Overwrite with Aegis example?"
            ):
                return

        with open(hook_path, "w", encoding="utf-8") as f:
            f.write(hook_content)

        if os.name != "nt":
            os.chmod(hook_path, 0o755)

        self.console.print(
            "[bold green]✅ Optional Git pre-commit hook"
            " wired successfully.[/bold green]"
        )

    def serve(
        self,
        transport: str = typer.Option(
            "stdio", "--transport", help="MCP transport: stdio, sse, or streamable-http"
        ),
        host: str = typer.Option("127.0.0.1", "--host", help="Bind host (SSE/HTTP)"),
        port: int = typer.Option(8000, "--port", help="Bind port (SSE/HTTP)"),
    ):
        """Starts the Aegis MCP server as a long-running process."""
        from aegis.kernel.server import AegisKernel

        self.console.print(
            f"[bold blue]Aegis Kernel starting[/bold blue] "
            f"(transport={transport}, host={host}, port={port})"
        )
        kernel = AegisKernel()
        kernel.run(transport=transport, host=host, port=port)

    def self_check(self):
        """Enforces the self-governance invariant by auditing Aegis itself."""
        self.console.print("[bold blue]Aegis Self-Governance Audit[/bold blue]")
        try:
            self.check(staged=False)
        except typer.Exit as e:
            if e.exit_code == 0:
                self.console.print(
                    "[bold green]✅ Aegis is compliant with its own laws.[/bold green]"
                )
            else:
                self.console.print(
                    "[bold red]❌ Self-governance violation detected![/bold red]"
                )
            raise e

    def run(self):
        self.app()

    @staticmethod
    def entry_point():

        # Basic logging config
        logging.basicConfig(
            level=(
                logging.WARNING if "AEGIS_VERBOSE" not in os.environ else logging.DEBUG
            ),
        )
        cli = AegisCLI()
        cli.run()


cli = AegisCLI()
app = cli.app


if __name__ == "__main__":
    AegisCLI.entry_point()
