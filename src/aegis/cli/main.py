import os
import typer
from typing import Optional, List
from rich.console import Console
from rich.prompt import Prompt, Confirm
from aegis.core.container.app import Container
from aegis.core.models.governance import EnforcementMode
from aegis.core.models.evolution import EvolutionDecision

class AegisCLI:
    """
    Encapsulates the CLI logic within a class to comply with Strict OOD.
    """
    def __init__(self):
        self.container = Container()
        self.console = Console()
        self.app = typer.Typer(help="Aegis: Agentic Architectural Governance Engine")
        self._register_commands()

    def _register_commands(self):
        self.app.command()(self.status)
        self.app.command()(self.init)
        self.app.command()(self.check)
        self.app.command()(self.baseline)
        self.app.command()(self.apply)
        self.app.command()(self.evolve)
        self.app.command()(self.setup_hooks)
        self.app.command()(self.self_check)

    def status(self):
        """Displays the current architectural governance status."""
        self.console.print("[bold blue]Aegis Governance Dashboard[/bold blue]")
        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        if not os.path.exists(rules_path):
            self.console.print("[yellow]Project not yet initialized or rules.yaml missing.[/yellow]")
            return
        rules = self.container.policy_parser.parse_rules(rules_path)
        self.console.print(f"\n[bold]Active Rules ({len(rules)}):[/bold]")
        for r in rules:
            mode_style = "red" if r.mode == EnforcementMode.BLOCK else "yellow"
            self.console.print(f"- [cyan]{r.id}[/cyan]: {r.description} ([dim]{r.language}[/dim]) [{mode_style}]{r.mode.value}[/{mode_style}]")
        baseline = self.container.baseline_manager.load_baseline_raw()
        self.console.print(f"\n[bold]Technical Debt Baseline:[/bold]")
        self.console.print(f"- Total violations: {len(baseline)}")
        log = self.container.evolution_service.load_log()
        self.console.print(f"\n[bold]Recent Evolution Decisions ({len(log.decisions)}):[/bold]")
        for d in log.decisions[-3:]:
            self.console.print(f"- [dim]{d.timestamp.strftime('%Y-%m-%d')}[/dim] [bold]{d.rule_id}[/bold]: {d.action} ({d.rationale})")

    def init(self):
        """Initialize Aegis governance directory structure."""
        aegis_dir = os.path.join(self.container.workspace_root, ".aegis")
        if os.path.exists(aegis_dir):
            self.console.print("[green].aegis/ already exists. Run `/aegis-update` in Claude Code to review governance.[/green]")
            return
        os.makedirs(aegis_dir)
        config_path = os.path.join(aegis_dir, "config.yaml")
        with open(config_path, "w", encoding="utf-8") as f:
            f.write("enforcement: warn\n")
        self.console.print("[green].aegis/ created. Run `/aegis-init` in Claude Code to set up governance rules.[/green]")

    def check(
        self,
        staged: bool = typer.Option(False, "--staged", help="Check only staged changes (pre-commit mode)"),
        rule: Optional[str] = typer.Option(None, "--rule", help="Filter check by specific rule ID")
    ):
        """Performs a gated compliance check. Exits with code 1 if NEW architectural violations are detected."""
        self.console.print("[bold blue]Aegis Enforcement Gate[/bold blue]")
        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        if not os.path.exists(rules_path):
            self.console.print("[red]Error: rules.yaml missing.[/red]")
            raise typer.Exit(code=1)
        all_rules = self.container.policy_parser.parse_rules(rules_path)
        rules = [r for r in all_rules if r.id == rule] if rule else all_rules
        if staged:
            self.console.print("Evaluating staged changes...")
            violations = self.container.evaluation_service.evaluate_changes(rules)
        else:
            self.console.print("Performing full workspace check...")
            violations = self.container.evaluation_service.evaluate_workspace(self.container.workspace_root, rules)
        active_violations = [v for v in violations if not self.container.baseline_manager.is_exempt(v)]
        if not active_violations:
            self.console.print("\n[bold green]✅ Gated check passed.[/bold green]")
            if len(violations) > 0:
                self.console.print(f"[dim](Ignored {len(violations)} legacy violations in baseline)[/dim]")
            return
        blocking_violations = []
        warning_violations = []
        rule_map = {r.id: r for r in rules}
        for v in active_violations:
            r = rule_map.get(v.rule_id)
            if r and r.mode == EnforcementMode.BLOCK:
                blocking_violations.append(v)
            else:
                warning_violations.append(v)
        if warning_violations:
            self.console.print(f"\n[yellow][!] Found {len(warning_violations)} non-blocking violations:[/yellow]")
            for v in warning_violations:
                 self.console.print(f"- [bold]{v.severity}[/bold] {v.file}:{v.line} - {v.description} ({v.rule_id})")
        if blocking_violations:
            self.console.print(f"\n[bold red][!] BLOCKING: Found {len(blocking_violations)} NEW Architectural Violations:[/bold red]")
            for v in blocking_violations:
                self.console.print(f"- [bold]{v.severity}[/bold] {v.file}:{v.line} - {v.description} ({v.rule_id})")
            raise typer.Exit(code=1)
        else:
            self.console.print("\n[bold green]✅ Gated check passed (No blocking violations).[/bold green]")

    def baseline(
        self,
        clear: bool = typer.Option(False, "--clear", help="Clear the existing baseline"),
        diff: bool = typer.Option(False, "--diff", help="Show violations not in current baseline")
    ):
        """Captures all current architectural violations and stores them in .aegis/baseline.json."""
        self.console.print("[bold blue]Aegis Baseline Management[/bold blue]")
        if clear:
            if os.path.exists(self.container.baseline_manager.path):
                os.remove(self.container.baseline_manager.path)
                self.console.print("[yellow]Baseline cleared.[/yellow]")
            return
        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        rules = self.container.policy_parser.parse_rules(rules_path)
        violations = self.container.evaluation_service.evaluate_workspace(self.container.workspace_root, rules)
        if diff:
            new_violations = [v for v in violations if not self.container.baseline_manager.is_exempt(v)]
            self.console.print(f"Found {len(new_violations)} violations not in baseline.")
            for v in new_violations:
                self.console.print(f"- {v.file}:{v.line} ({v.rule_id})")
            return
        self.container.baseline_manager.save_baseline(violations)
        self.console.print(f"[green]Successfully baselined {len(violations)} violations.[/green]")

    def apply(self, rule: Optional[str] = None):
        """Applies automated remediation to resolve architectural violations."""
        self.console.print("[bold blue]Aegis Architectural Remediation[/bold blue]")
        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        all_rules = self.container.policy_parser.parse_rules(rules_path)
        rules = [r for r in all_rules if r.id == rule] if rule else all_rules
        violations = self.container.evaluation_service.evaluate_workspace(self.container.workspace_root, rules)
        active_violations = [v for v in violations if not self.container.baseline_manager.is_exempt(v)]
        if not active_violations:
            self.console.print("[green]No active violations found.[/green]")
            return
        plan = self.container.remediation_service.create_plan(active_violations)
        for action in plan.actions:
            v = action.violation
            self.console.print(f"- [dim]{action.strategy}[/dim] Fix {v.file}:{v.line} ({v.rule_id})")
        if Confirm.ask("\nDo you want to apply these fixes?"):
            success_count = self.container.remediation_service.execute_plan(plan)
            self.console.print(f"\n[bold green]Success![/bold green] Applied {success_count} remediation actions.")

    def evolve(self, rule_id: str = typer.Argument(..., help="The ID of the rule to evolve")):
        """Initiates a consensus loop to modify an architectural invariant."""
        self.console.print(f"[bold blue]Aegis Architectural Evolution: {rule_id}[/bold blue]")
        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        rules = self.container.policy_parser.parse_rules(rules_path)
        rule = next((r for r in rules if r.id == rule_id), None)
        if not rule:
            self.console.print(f"[red]Error: Rule '{rule_id}' not found.[/red]")
            return
        violations = self.container.evaluation_service.evaluate_workspace(self.container.workspace_root, [rule])
        active = [v for v in violations if not self.container.baseline_manager.is_exempt(v)]
        if active:
            self.console.print(f"\n[yellow]Found {len(active)} active violations for this rule.[/yellow]")
            if Confirm.ask("Do you want to suppress these violations (add to baseline)?"):
                for v in active:
                    self.container.baseline_manager.add_to_baseline(v)
                self.console.print(f"[green]Successfully suppressed {len(active)} violations.[/green]")
                return
        action = Prompt.ask("Action?", choices=["relax_rule", "refactor_required"], default="refactor_required")
        rationale = Prompt.ask("Rationale")
        self.container.evolution_service.log_decision(EvolutionDecision(rule_id=rule_id, action=action, rationale=rationale))
        self.console.print(f"\n✅ Decision recorded.")

    def setup_hooks(self):
        """Wires Aegis into the project's Git hooks."""
        git_dir = os.path.join(self.container.workspace_root, ".git")
        if not os.path.exists(git_dir):
            self.console.print("[red]Error: Not a Git repository.[/red]")
            return
        hook_path = os.path.join(git_dir, "hooks", "pre-commit")
        hook_content = f"#!/bin/sh\nuv run aegis check --staged\n"
        with open(hook_path, "w", encoding="utf-8") as f:
            f.write(hook_content)
        if os.name != "nt":
            os.chmod(hook_path, 0o755)
        self.console.print("[bold green]✅ Pre-commit hook installed.[/bold green]")

    def self_check(self):
        """Enforces the self-governance invariant by auditing Aegis itself."""
        self.console.print("[bold blue]Aegis Self-Governance Audit[/bold blue]")
        try:
            self.check(staged=False)
        except typer.Exit as e:
            if e.exit_code == 0:
                self.console.print("[bold green]✅ Aegis is compliant with its own laws.[/bold green]")
            else:
                self.console.print("[bold red]❌ Self-governance violation detected![/bold red]")
            raise e

def main():
    cli = AegisCLI()
    cli.app()

cli = AegisCLI()
app = cli.app

if __name__ == "__main__":
    main()
