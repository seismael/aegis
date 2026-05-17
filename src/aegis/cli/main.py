import os
import typer
import json
from typing import Optional, List
from rich.console import Console
from rich.prompt import Prompt, Confirm
from aegis.core.container.app import Container
from aegis.core.models.governance import EnforcementMode
from aegis.core.models.evolution import EvolutionDecision

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

    def _register_commands(self):
        self.app.command()(self.install)
        self.app.command()(self.init)
        self.app.command()(self.check)
        self.app.command()(self.baseline)
        self.app.command()(self.status)
        self.app.command()(self.apply)
        self.app.command()(self.evolve)
        self.app.command()(self.setup_hooks)
        self.app.command()(self.self_check)

    def install(self):
        """Global installation proxy for the CLI."""
        from aegis.infrastructure.installer import AegisInstaller
        AegisInstaller.entry_point()

    def init(self):
        """
        Initializes Aegis governance for the CURRENT project.
        Sets up the .aegis/ directory and wires Git pre-commit hooks.
        """
        aegis_dir = os.path.join(self.container.workspace_root, ".aegis")
        if not os.path.exists(aegis_dir):
            os.makedirs(aegis_dir)
            self.console.print(f"[green]Initialized .aegis/ at {aegis_dir}[/green]")
        
        # 1. Create minimal project config
        config_path = os.path.join(aegis_dir, "config.yaml")
        if not os.path.exists(config_path):
            with open(config_path, "w", encoding="utf-8") as f:
                f.write("enforcement: warn\n")
        
        # 2. Wire Git hooks automatically during init
        self.setup_hooks()
        
        self.console.print("\n[bold green]Project Governance Active![/bold green]")
        self.console.print("Run `/aegis-init` in your AI chat to begin architectural discovery.")

    def check(
        self,
        staged: bool = typer.Option(False, "--staged", help="Check only staged changes"),
        rule: Optional[str] = typer.Option(None, "--rule", help="Filter by specific rule ID"),
        strict: bool = typer.Option(False, "--strict", help="Treat warnings/reports as blocking")
    ):
        """Performs a gated compliance check. Non-zero exit on blocking violations."""
        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        if not os.path.exists(rules_path):
            self.console.print("[red]Error: .aegis/rules.yaml not found. Run 'aegis init' first.[/red]")
            raise typer.Exit(code=1)

        all_rules = self.container.policy_parser.parse_rules(rules_path)
        rules = [r for r in all_rules if r.id == rule] if rule else all_rules
        
        if staged:
            violations = self.container.evaluation_service.evaluate_changes(rules)
        else:
            violations = self.container.evaluation_service.evaluate_workspace(self.container.workspace_root, rules)
            
        active = [v for v in violations if not self.container.baseline_manager.is_exempt(v)]
        
        if not active:
            self.console.print("[green]✅ Architecture compliant.[/green]")
            return

        # Blocking logic
        rule_map = {r.id: r for r in rules}
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
            mode = r_obj.mode.value if r_obj else "warn" # Default to warn for unknown rules
            style = "red" if mode == "block" else "yellow"
            self.console.print(f"- [{style}]{mode.upper()}[/{style}] {v.file}:{v.line} ({v.rule_id})")

        if blocking:
            self.console.print(f"\n[bold red]Blocked: {len(blocking)} architectural violations detected.[/bold red]")
            raise typer.Exit(code=1)

    def baseline(self, clear: bool = typer.Option(False, "--clear", help="Clear the existing baseline")):
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
        violations = self.container.evaluation_service.evaluate_workspace(self.container.workspace_root, rules)
        self.container.baseline_manager.save_baseline(violations)
        self.console.print(f"[green]Successfully baselined {len(violations)} violations.[/green]")

    def status(self, json_output: bool = typer.Option(False, "--json")):
        """Provides a summary of the current governance state."""
        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        rules = self.container.policy_parser.parse_rules(rules_path)
        baseline = self.container.baseline_manager.load_baseline_raw()
        
        stats = {
            "rules_count": len(rules),
            "baseline_violations": len(baseline),
            "project_root": self.container.workspace_root
        }
        
        if json_output:
            print(json.dumps(stats))
        else:
            self.console.print(f"Aegis Status: {len(rules)} rules, {len(baseline)} legacy debt items.")

    def apply(self, rule: Optional[str] = typer.Option(None, "--rule", help="Specific rule to remediate")):
        """Displays remediation prompts for active violations."""
        self.console.print("[bold blue]Aegis Architectural Remediation Audit[/bold blue]")
        
        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        if not os.path.exists(rules_path):
            self.console.print("[red]Error: .aegis/rules.yaml not found.[/red]")
            return

        all_rules = self.container.policy_parser.parse_rules(rules_path)
        rules = [r for r in all_rules if r.id == rule] if rule else all_rules
        
        violations = self.container.evaluation_service.evaluate_workspace(self.container.workspace_root, rules)
        active = [v for v in violations if not self.container.baseline_manager.is_exempt(v)]
        
        if not active:
            self.console.print("[green]No active violations found for remediation.[/green]")
            return

        self.console.print(f"Found {len(active)} active violations.")
        
        for v in active:
            self.console.print(f"\n[bold]Violation in {v.file}:{v.line} ({v.rule_id})[/bold]")
            prompt = f"REFACTORING STRATEGY: {v.description}"
            self.console.print(f"[dim]{prompt}[/dim]")
            
        self.console.print("\n[yellow]Note: In the Agentic paradigm, the AI agent performs the refactor.[/yellow]")

    def evolve(self, rule_id: str = typer.Argument(..., help="The ID of the rule to evolve")):
        """Consensus recording flow for rule modifications."""
        self.console.print(f"[bold blue]Aegis Architectural Evolution: {rule_id}[/bold blue]")
        
        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        if not os.path.exists(rules_path):
            self.console.print("[red]Error: .aegis/rules.yaml not found.[/red]")
            return

        rules = self.container.policy_parser.parse_rules(rules_path)
        rule = next((r for r in rules if r.id == rule_id), None)
        
        if not rule:
            self.console.print(f"[red]Error: Rule '{rule_id}' not found.[/red]")
            return

        action = Prompt.ask("Consensus Action?", choices=["suppress", "relax_rule", "refactor_required"], default="suppress")
        rationale = Prompt.ask("Decision Rationale")
        
        decision = EvolutionDecision(rule_id=rule_id, action=action, rationale=rationale)
        self.container.evolution_service.log_decision(decision)
        
        if action == "suppress":
            violations = self.container.evaluation_service.evaluate_workspace(self.container.workspace_root, [rule])
            for v in violations:
                self.container.baseline_manager.add_to_baseline(v)
            self.console.print(f"[green]Successfully suppressed {len(violations)} violations.[/green]")
        
        self.console.print("\n✅ Decision recorded in evolution_log.json")

    def setup_hooks(self):
        """Wires Aegis into the project's Git hooks."""
        git_dir = os.path.join(self.container.workspace_root, ".git")
        if not os.path.exists(git_dir):
            self.console.print("[yellow]Skipping Git hooks: Not a Git repository.[/yellow]")
            return
        hook_path = os.path.join(git_dir, "hooks", "pre-commit")
        hook_content = f"#!/bin/sh\naegis check --staged\n"
        with open(hook_path, "w", encoding="utf-8") as f:
            f.write(hook_content)
        if os.name != "nt":
            os.chmod(hook_path, 0o755)
        self.console.print("[bold green]✅ Git pre-commit hook wired.[/bold green]")

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

    def run(self):
        self.app()

    @staticmethod
    def entry_point():
        cli = AegisCLI()
        cli.run()

cli = AegisCLI()
app = cli.app

if __name__ == "__main__":
    AegisCLI.entry_point()
