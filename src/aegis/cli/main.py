import json
import logging
import os

import structlog
import typer
from rich.console import Console
from rich.prompt import Prompt

from aegis.core.container.app import Container
from aegis.core.models.evolution import EvolutionDecision
from aegis.core.models.governance import EnforcementMode


class AegisCLI:
    """
    Headless CLI for Aegis.
    Focused on CI/CD pipelines, environment bootstrapping, and diagnostic auditing.
    """

    def __init__(self):
        self.container = Container()
        self.console = Console()
        self.app = typer.Typer(help="Aegis: Headless Architectural Governance Engine")
        self._register_commands()

    def _register_commands(self):
        self.app.command()(self.install)
        self.app.command()(self.init)
        self.app.command()(self.check)
        self.app.command()(self.baseline)
        self.app.command()(self.status)
        self.app.command()(self.plugins)
        self.app.command()(self.apply)
        self.app.command()(self.evolve)
        self.app.command()(self.setup_hooks)
        self.app.command()(self.self_check)

    def install(self):
        """Globally installs Aegis MCP configurations and AI Skills."""
        from aegis.infrastructure.installer import UniversalInstaller

        self.console.print("[bold blue]Executing Aegis Universal Installation...[/bold blue]")
        try:
            installer = UniversalInstaller()
            installer.execute_global_install()
            self.console.print("[bold green]Installation complete. Aegis is now available natively in your AI tools.[/bold green]")
            self.console.print("Run `uv run aegis init` to initialize a project or `/aegis-init` in Claude Code.")
        except Exception as e:
            self.console.print(f"[bold red]Installation failed:[/bold red] {str(e)}")
            raise typer.Exit(code=1)

    def init(self):
        """Initializes the .aegis governance environment."""
        aegis_dir = os.path.join(self.container.workspace_root, ".aegis")
        if not os.path.exists(aegis_dir):
            os.makedirs(aegis_dir)

        # Create minimal config if missing
        config_path = os.path.join(aegis_dir, "config.yaml")
        if not os.path.exists(config_path):
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("enforcement: warn\n")

        self.console.print(
            f"[green]Aegis environment initialized at {aegis_dir}[/green]"
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
        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        if not os.path.exists(rules_path):
            self.console.print("[red]Error: .aegis/rules.yaml not found.[/red]")
            raise typer.Exit(code=1)

        all_rules = self.container.policy_parser.parse_rules(rules_path)
        rules = [r for r in all_rules if r.id == rule] if rule else all_rules

        if staged:
            violations = self.container.evaluation_service.evaluate_changes(rules)
        else:
            violations = self.container.evaluation_service.evaluate_workspace(
                self.container.workspace_root, rules
            )

        active = [
            v for v in violations if not self.container.baseline_manager.is_exempt(v)
        ]

        if not active:
            self.console.print("[green]Architecture compliant.[/green]")
            return

        # Blocking logic
        rule_map = {r.id: r for r in rules}
        blocking_modes = {EnforcementMode.BLOCK}
        if strict:
            blocking_modes.add(EnforcementMode.WARN)
            blocking_modes.add(EnforcementMode.REPORT)
        blocking = [v for v in active if rule_map.get(v.rule_id).mode in blocking_modes]

        for v in active:
            r_obj = rule_map.get(v.rule_id)
            mode = r_obj.mode.value if r_obj else "unknown"
            style = "red" if mode == "block" else "yellow"
            try:
                rel = os.path.relpath(v.file, self.container.workspace_root)
            except ValueError:
                rel = v.file
            self.console.print(
                f"  [{style}]{mode.upper():>5}[/{style}]  {rel}:{v.line}  ({v.rule_id})"
            )

        if blocking:
            self.console.print(
                f"\n[bold red]Blocked: {len(blocking)} architectural violations detected.[/bold red]"
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
            if os.path.exists(self.container.baseline_manager.path):
                os.remove(self.container.baseline_manager.path)
            self.console.print("[yellow]Baseline cleared.[/yellow]")
            return

        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        if not os.path.exists(rules_path):
            self.console.print("[red]Error: .aegis/rules.yaml not found.[/red]")
            return

        rules = self.container.policy_parser.parse_rules(rules_path)
        violations = self.container.evaluation_service.evaluate_workspace(
            self.container.workspace_root, rules
        )
        self.container.baseline_manager.save_baseline(violations)
        self.console.print(
            f"[green]Successfully baselined {len(violations)} violations.[/green]"
        )

    def status(self, json_output: bool = typer.Option(False, "--json")):
        """Provides a summary of the current governance state."""
        from rich.table import Table

        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        rules = self.container.policy_parser.parse_rules(rules_path)
        baseline = self.container.baseline_manager.load_baseline_raw()

        # Count active violations per rule
        violations = self.container.evaluation_service.evaluate_workspace(
            self.container.workspace_root, rules
        )
        baseline_map = {(v.file, v.line, v.rule_id) for v in baseline}
        active_counts = {r.id: 0 for r in rules}
        for v in violations:
            if (v.file, v.line, v.rule_id) not in baseline_map:
                active_counts[v.rule_id] = active_counts.get(v.rule_id, 0) + 1

        engine_counts: dict[str, int] = {}
        for r in rules:
            engine_counts[r.engine_type.value] = (
                engine_counts.get(r.engine_type.value, 0) + 1
            )

        loaded_plugins = self.container.loaded_plugins
        stats = {
            "rules_count": len(rules),
            "baseline_violations": len(baseline),
            "active_violations": sum(active_counts.values()),
            "engines": engine_counts,
            "plugins": len(loaded_plugins),
            "project_root": self.container.workspace_root,
            "rules": [
                {
                    "id": r.id,
                    "engine": r.engine_type.value,
                    "severity": r.severity.value,
                    "mode": r.mode.value,
                    "language": r.language,
                    "active_violations": active_counts.get(r.id, 0),
                    "baseline_entries": sum(1 for v in baseline if v.rule_id == r.id),
                }
                for r in rules
            ],
        }

        if json_output:
            print(json.dumps(stats, indent=2))
            return

        # Summary line
        self.console.print(
            f"[bold]Aegis Status:[/bold] {len(rules)} rules, "
            f"{len(baseline)} baselined, "
            f"{stats['active_violations']} active violations"
        )

        # Per-engine breakdown
        engine_summary = " | ".join(
            f"{count}x {engine}" for engine, count in sorted(engine_counts.items())
        )
        self.console.print(f"  Engines: {engine_summary}")
        if loaded_plugins:
            self.console.print(
                f"  Plugins: {len(loaded_plugins)} loaded ({', '.join(loaded_plugins)})"
            )

        # Rule table
        table = Table(show_header=True, header_style="bold")
        table.add_column("Rule ID")
        table.add_column("Engine")
        table.add_column("Severity")
        table.add_column("Mode")
        table.add_column("Active")
        table.add_column("Baselined")

        for r in rules:
            active = active_counts.get(r.id, 0)
            baselined = sum(1 for v in baseline if v.rule_id == r.id)
            mode_style = {
                "block": "red",
                "warn": "yellow",
                "report": "dim",
                "silent": "dim",
            }.get(r.mode.value, "")
            table.add_row(
                r.id,
                r.engine_type.value,
                r.severity.value,
                f"[{mode_style}]{r.mode.value}[/{mode_style}]",
                str(active) if active else "0",
                str(baselined) if baselined else "0",
            )
        self.console.print(table)

    def plugins(self):
        """Lists loaded plugins and their capabilities."""
        loaded = self.container.loaded_plugins
        if not loaded:
            self.console.print("[dim]No plugins loaded.[/dim]")
            return

        from rich.table import Table

        table = Table(show_header=True, header_style="bold")
        table.add_column("Plugin")
        table.add_column("Analyzers")
        table.add_column("MCP Tools")
        for name in loaded:
            table.add_row(name, "yes", "yes")
        self.console.print(table)

    def apply(
        self,
        rule: str | None = typer.Option(
            None, "--rule", help="Specific rule to remediate"
        ),
    ):
        """Displays remediation prompts for active violations."""
        self.console.print(
            "[bold blue]Aegis Architectural Remediation Audit[/bold blue]"
        )

        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        all_rules = self.container.policy_parser.parse_rules(rules_path)
        rules = [r for r in all_rules if r.id == rule] if rule else all_rules

        violations = self.container.evaluation_service.evaluate_workspace(
            self.container.workspace_root, rules
        )
        active = [
            v for v in violations if not self.container.baseline_manager.is_exempt(v)
        ]

        if not active:
            self.console.print(
                "[green]No active violations found for remediation.[/green]"
            )
            return

        self.console.print(f"Found {len(active)} active violations.")

        for v in active:
            self.console.print(
                f"\n[bold]Violation in {v.file}:{v.line} ({v.rule_id})[/bold]"
            )
            # Simulate the kernel's prompt generation
            prompt = f"REFACTORING STRATEGY: {v.description}"
            self.console.print(f"[dim]{prompt}[/dim]")

        self.console.print(
            "\n[yellow]Note: In the Agentic paradigm, the AI agent performs the refactor.[/yellow]"
        )
        self.console.print(
            "Run `/aegis-rule-add` or `/aegis-update` in your AI chat to trigger a fix."
        )

    def evolve(
        self, rule_id: str = typer.Argument(..., help="The ID of the rule to evolve")
    ):
        """Consensus recording flow for rule modifications."""
        self.console.print(
            f"[bold blue]Aegis Architectural Evolution: {rule_id}[/bold blue]"
        )

        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        rules = self.container.policy_parser.parse_rules(rules_path)
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
        self.container.evolution_service.log_decision(decision)

        if action == "suppress":
            self.console.print(
                "[yellow]Capturing current violations for this rule into baseline...[/yellow]"
            )
            violations = self.container.evaluation_service.evaluate_workspace(
                self.container.workspace_root, [rule]
            )
            for v in violations:
                self.container.baseline_manager.add_to_baseline(v)
            self.console.print(
                f"[green]Successfully suppressed {len(violations)} violations.[/green]"
            )

        self.console.print("\nDecision recorded in evolution_log.json")

    def setup_hooks(self):
        """Wires Aegis into the project's Git hooks."""
        git_dir = os.path.join(self.container.workspace_root, ".git")
        if not os.path.exists(git_dir):
            self.console.print("[red]Error: Not a Git repository.[/red]")
            return
        hook_path = os.path.join(git_dir, "hooks", "pre-commit")
        hook_content = "#!/bin/sh\nuv run aegis check --staged\n"
        with open(hook_path, "w", encoding="utf-8") as f:
            f.write(hook_content)
        if os.name != "nt":
            os.chmod(hook_path, 0o755)
        self.console.print("[bold green]Pre-commit hook installed.[/bold green]")

    def self_check(self):
        """Enforces the self-governance invariant by auditing Aegis itself."""
        self.console.print("[bold blue]Aegis Self-Governance Audit[/bold blue]")
        try:
            self.check(staged=False)
        except typer.Exit as e:
            if e.exit_code == 0:
                self.console.print(
                    "[bold green]Aegis is compliant with its own laws.[/bold green]"
                )
            else:
                self.console.print(
                    "[bold red]Self-governance violation detected![/bold red]"
                )
            raise e

    def run(self):
        self.app()

    @staticmethod
    def entry_point():
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(
                logging.WARNING if "AEGIS_VERBOSE" not in os.environ else logging.DEBUG
            ),
        )
        cli = AegisCLI()
        cli.run()


cli = AegisCLI()
app = cli.app

if __name__ == "__main__":
    AegisCLI.entry_point()
