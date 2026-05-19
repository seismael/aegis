import json
import logging
import os
import sys
from collections import Counter

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

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
        self._container = container
        self.console = Console()
        self.app = typer.Typer(help="Aegis: Headless Architectural Governance Engine")
        self._register_commands()

    @property
    def container(self) -> Container:
        if self._container is None:
            self._container = Container()
        return self._container

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
        self.app.command()(self.fix)
        self.app.command()(self.evolve)
        self.app.command()(self.setup_hooks)
        self.app.command()(self.serve)
        self.app.command()(self.watch)
        self.app.command()(self.self_check)
        self.app.add_typer(
            self._rules_app, name="rules", help="Manage governance rule packs"
        )
        self.app.add_typer(
            self._plugin_app, name="plugin", help="Create and manage Aegis plugins"
        )

    @property
    def _rules_app(self) -> typer.Typer:
        """Sub-command group for rule pack lifecycle management."""

        rules_cmd = typer.Typer(help="Manage architectural rule packs")

        @rules_cmd.command("list")
        def rules_list(
            verbose: bool = typer.Option(
                False, "--verbose", "-v", help="Show per-pack rule counts"
            ),
        ):
            """List installed and available rule packs."""
            pm = self.container.rule_pack_manager
            installed = pm.list_installed()
            available = pm.list_available()

            if available:
                self.console.print("\n[bold]Available rule packs:[/bold]")
                table = Table(box=None, padding=(0, 2))
                table.add_column("Pack", style="cyan", width=22)
                table.add_column("Description", style="white", ratio=1)
                table.add_column("Status", width=18)
                if verbose:
                    table.add_column("Version", width=12)
                    table.add_column("Author", style="dim", width=16)
                for name, meta in available.items():
                    status = (
                        "[green]installed[/green]"
                        if name in installed
                        else "[dim]not installed[/dim]"
                    )
                    if verbose:
                        table.add_row(
                            name,
                            meta.description,
                            status,
                            f"v{meta.version}",
                            meta.author,
                        )
                    else:
                        table.add_row(name, meta.description, status)
                self.console.print(table)

            custom = pm.list_custom()
            if custom:
                self.console.print("\n[bold]Custom (unpackaged) rules:[/bold]")
                for f in custom:
                    self.console.print(f"  {f}")

            if not available and not custom:
                self.console.print("[yellow]No rule packs found.[/yellow]")

        @rules_cmd.command("install")
        def rules_install(
            pack_name: str = typer.Argument(..., help="Pack name to install"),
        ):
            """Install a rule pack from Aegis defaults."""
            pm = self.container.rule_pack_manager
            try:
                pm.install(pack_name)
                self.console.print(f"[green]Installed '{pack_name}' rule pack.[/green]")
            except ValueError as e:
                self.console.print(f"[red]{e}[/red]")
                raise typer.Exit(code=1) from e

        @rules_cmd.command("remove")
        def rules_remove(
            pack_name: str = typer.Argument(..., help="Pack name to remove"),
        ):
            """Remove an installed rule pack."""
            pm = self.container.rule_pack_manager
            try:
                pm.remove(pack_name)
                self.console.print(f"[green]Removed '{pack_name}' rule pack.[/green]")
            except ValueError as e:
                self.console.print(f"[red]{e}[/red]")
                raise typer.Exit(code=1) from e

        @rules_cmd.command("update")
        def rules_update(
            pack_name: str | None = typer.Argument(
                None, help="Pack to update (omit to update all)"
            ),
        ):
            """
            Update installed pack(s) to latest defaults,
            preserving custom overrides.
            """
            pm = self.container.rule_pack_manager
            updated = pm.update(pack_name)
            if updated:
                self.console.print(f"[green]Updated: {', '.join(updated)}[/green]")
            else:
                self.console.print("[yellow]All packs are up-to-date.[/yellow]")

        @rules_cmd.command("reset")
        def rules_reset(
            yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
        ):
            """Remove all installed packs (preserves custom root-level rules)."""
            pm = self.container.rule_pack_manager
            installed = pm.list_installed()
            if not installed:
                self.console.print("[yellow]No packs installed.[/yellow]")
                return

            if not yes:
                names = ", ".join(installed.keys())
                result = Confirm.ask(
                    f"Remove all {len(installed)} installed pack(s): {names}?"
                )
                if not result:
                    self.console.print("[dim]Cancelled.[/dim]")
                    return

            pm.reset()
            self.console.print(
                "[green]All packs removed. Custom rules preserved.[/green]"
            )

        @rules_cmd.command("create")
        def rules_create(
            pack_name: str = typer.Argument(..., help="Name for the new custom pack"),
            file: str | None = typer.Option(
                None, "--file", "-f", help="YAML file with rule definitions"
            ),
        ):
            """Create a custom rule pack from YAML rule definitions."""
            if file:
                if not os.path.isfile(file):
                    self.console.print(f"[red]File not found: {file}[/red]")
                    raise typer.Exit(code=1)
                import yaml as ymlib

                with open(file, encoding="utf-8") as f:
                    data = ymlib.safe_load(f)
                rules = data.get("rules", []) if isinstance(data, dict) else []
            else:
                self.console.print(
                    "[yellow]No --file provided. Creating empty pack.[/yellow]"
                )
                rules = []

            pm = self.container.rule_pack_manager
            try:
                path = pm.create(pack_name, rules)
                self.console.print(
                    f"[green]Created custom pack '{pack_name}' at {path}[/green]"
                )
            except ValueError as e:
                self.console.print(f"[red]{e}[/red]")
                raise typer.Exit(code=1) from e

        @rules_cmd.command("phases")
        def rules_phases():
            """List evaluation phases with rule counts."""
            all_rules = self.container.load_rules()
            from aegis.domain.policy.models import EvaluationPhase

            phase_counts: dict[str, int] = {}
            mapping = self.container.category_phase_mapping

            for p in EvaluationPhase:
                filtered = [
                    r
                    for r in all_rules
                    if r.phases is not None
                    and p in r.phases
                    or r.phases is None
                    and p in mapping.category_defaults.get(r.category, [])
                ]
                phase_counts[p.value] = len(filtered)

            self.console.print("\n[bold]Evaluation phases:[/bold]")
            for phase_name in sorted(phase_counts.keys()):
                count = phase_counts[phase_name]
                self.console.print(f"  {phase_name:20s} {count} rules")

        @rules_cmd.command("phase-mapping")
        def rules_phase_mapping():
            """Show the current category-to-phase mapping."""
            mapping = self.container.category_phase_mapping
            self.console.print("\n[bold]Category -> Phase mapping:[/bold]")
            for cat, phases in sorted(mapping.category_defaults.items()):
                phase_str = ", ".join(p.value for p in phases)
                self.console.print(f"  {cat.value:20s} -> {phase_str}")

        return rules_cmd

    @property
    def _plugin_app(self) -> typer.Typer:
        """Sub-command group for plugin lifecycle management."""
        plugin_cmd = typer.Typer(help="Create and manage Aegis plugins")

        @plugin_cmd.command("create")
        def plugin_create(
            name: str = typer.Argument(
                ..., help="Name for the new plugin (e.g. my-custom-analyzer)"
            ),
        ):
            """Scaffold a new Aegis plugin in .aegis/plugins/."""
            from aegis.core.plugins.scaffold import PluginScaffold

            plugin_dir = os.path.join(
                self.container.workspace_root, ".aegis", "plugins"
            )
            try:
                path = PluginScaffold.create(plugin_dir, name)
                self.console.print(
                    f"[green]Plugin scaffold created: {path}[/green]"
                )
            except ValueError as e:
                self.console.print(f"[red]{e}[/red]")
                raise typer.Exit(code=1) from e

        return plugin_cmd

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
        exit_code: bool = typer.Option(
            False,
            "--exit-code",
            help="Exit non-zero on ANY violation (for CI pipelines)",
        ),
        phase: str | None = typer.Option(
            None,
            "--phase",
            help="Evaluation phase: pre-commit, pre-push, ci, nightly, on-demand",
        ),
        category: str | None = typer.Option(
            None, "--category", help="Filter by rule category"
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

        # --staged implies --phase pre-commit unless explicitly overridden
        effective_phase = phase
        if staged and not phase:
            effective_phase = "pre-commit"

        if effective_phase or category:
            all_rules = self.container.load_rules_for_phase(
                phase=effective_phase, category=category
            )

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

        # --exit-code: any active violation makes the pipeline fail
        if exit_code and active:
            blocking = list(active)  # mark ALL active violations as blocking

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
        show: bool = typer.Option(
            False, "--show", help="Display current baseline contents"
        ),
        prune: bool = typer.Option(
            False, "--prune", help="Remove baseline entries for deleted rules"
        ),
        expire_days: int | None = typer.Option(
            None, "--expire-days", help="Remove entries older than N days"
        ),
    ):
        """Manages the architectural technical debt ledger."""
        bm = self.container.baseline_manager
        if not bm:
            self.console.print(
                "[red]Error: Baseline manager unavailable"
                " — container running in degraded mode.[/red]"
            )
            return

        if clear:
            if os.path.exists(bm.path):
                os.remove(bm.path)
            self.console.print("[yellow]Baseline cleared.[/yellow]")
            return

        if show:
            summary = bm.show_baseline()
            self.console.print(summary)
            return

        if prune:
            rules = self.container.load_rules()
            active_ids = {r.id for r in rules}
            removed = bm.prune_stale(active_ids)
            self.console.print(
                f"[green]Pruned {removed} stale baseline entries.[/green]"
                if removed
                else "[yellow]No stale entries to prune.[/yellow]"
            )
            return

        if expire_days is not None:
            rules = self.container.load_rules()
            active_ids = {r.id for r in rules}
            removed = bm.expire_old(expire_days, active_ids)
            self.console.print(
                f"[green]Expired {removed} baseline entries older "
                f"than {expire_days} days.[/green]"
                if removed
                else "[yellow]No expired entries found.[/yellow]"
            )
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
            engine_str = ", ".join(
                f"{name}: {count}" for name, count in sorted(engine_counts.items())
            )
            self.console.print(
                f"[bold]Aegis Status[/bold] — "
                f"{len(rules)} rules, "
                f"{len(active_violations)} active, "
                f"{len(baseline)} baselined"
            )
            self.console.print(f"  Engines: {engine_str}")
            if self.container.loaded_plugins:
                self.console.print(
                    f"  Plugins: {', '.join(self.container.loaded_plugins)}"
                )
            self.console.print(f"  Project: {self.container.workspace_root}")

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

    def fix(
        self,
        dry_run: bool = typer.Option(
            False, "--dry-run", help="Show what would be fixed without modifying files"
        ),
        rule: str | None = typer.Option(
            None, "--rule", help="Specific rule to fix (omit for all fixable rules)"
        ),
    ):
        """Apply auto-fixes to deterministic, fixable violations."""
        from aegis.domain.enforcement.fixer import (
            apply_fixes,
            list_fixable_rule_ids,
        )

        all_rules = self.container.load_rules()
        if not all_rules:
            self.console.print("[red]Error: No rules found.[/red]")
            raise typer.Exit(code=1)

        fixable_ids = list_fixable_rule_ids()
        if rule:
            if rule not in fixable_ids:
                self.console.print(
                    f"[yellow]Rule '{rule}' has no auto-fix registered.[/yellow]"
                )
                return
            rules = [r for r in all_rules if r.id == rule]
        else:
            rules = [r for r in all_rules if r.id in fixable_ids]

        if not rules:
            self.console.print("[yellow]No fixable rules found.[/yellow]")
            return

        rule_map = {r.id: r for r in all_rules}
        self._require_governance()
        violations = self.container.governance_service.get_active_violations(
            rules, self.container.workspace_root
        )

        if not violations:
            self.console.print("[green]No fixable violations found.[/green]")
            return

        results = apply_fixes(violations, rule_map, dry_run=dry_run)
        fixed = [r for r in results if r.fixed]
        failed = [r for r in results if not r.fixed]

        if fixed:
            for r in fixed:
                self.console.print(
                    f"  [green]FIXED[/green] {r.file}:{r.line} ({r.rule_id})"
                )
        if failed:
            for r in failed:
                self.console.print(
                    f"  [red]FAIL[/red] {r.file}:{r.line} — {r.message}"
                )

        count = len(fixed)
        if dry_run:
            self.console.print(
                f"\n[bold yellow]Dry-run:"
                f" {count} violations would be fixed.[/bold yellow]"
            )
        else:
            self.console.print(
                f"\n[bold green]Auto-fixed {len(fixed)} violations.[/bold green]"
            )

    def evolve(
        self,
        rule_id: str = typer.Argument(..., help="The ID of the rule to evolve"),
        action: str | None = typer.Option(
            None,
            "--action",
            help="Non-interactive mode: suppress, relax_rule, or refactor_required",
        ),
        rationale: str | None = typer.Option(
            None, "--rationale", help="Decision rationale (required with --action)"
        ),
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

        if action is not None or rationale is not None:
            if action not in ("suppress", "relax_rule", "refactor_required", None):
                self.console.print(
                    f"[red]Error: Invalid action '{action}'. "
                    "Choose suppress, relax_rule, or refactor_required.[/red]"
                )
                return
            if action is None:
                self.console.print(
                    "[red]Error: --action is required"
                    " when --rationale is provided.[/red]"
                )
                return
            if not rationale:
                self.console.print(
                    "[red]Error: --rationale is required"
                    " when --action is provided.[/red]"
                )
                return
        else:
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

        self.console.print("\nOK Decision recorded in evolution_log.json")

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
            'echo "[Aegis] Validating architectural compliance..."\n'
            "aegis check --staged\n"
            "\n"
            "if [ $? -ne 0 ]; then\n"
            '  echo "[Aegis] Architectural drift detected. Commit blocked."\n'
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
            "[bold green]Optional Git pre-commit hook wired successfully.[/bold green]"
        )

    def serve(
        self,
        transport: str = typer.Option(
            "stdio", "--transport", help="MCP transport: stdio, sse, or streamable-http"
        ),
        host: str = typer.Option("127.0.0.1", "--host", help="Bind host (SSE/HTTP)"),
        port: int = typer.Option(8000, "--port", help="Bind port (SSE/HTTP)"),
        cors_origins: str | None = typer.Option(
            None, "--cors-origins",
            help="Comma-separated CORS origins (SSE/HTTP only)",
        ),
    ):
        """Starts the Aegis MCP server as a long-running process."""
        from aegis.kernel.server import AegisKernel

        self.console.print(
            f"[bold blue]Aegis Kernel starting[/bold blue] "
            f"(transport={transport}, host={host}, port={port})"
        )
        kernel = AegisKernel()
        kernel.run(
            transport=transport, host=host, port=port, cors_origins=cors_origins
        )

    def watch(
        self,
        interval: float = typer.Option(
            2.0, "--interval", "-i", help="Poll interval in seconds"
        ),
        phase: str | None = typer.Option(
            None, "--phase", help="Filter by evaluation phase"
        ),
        category: str | None = typer.Option(
            None, "--category", "-c", help="Filter by rule category"
        ),
        rule: str | None = typer.Option(
            None, "--rule", "-r", help="Filter by single rule ID"
        ),
        json_output: bool = typer.Option(
            False, "--json", help="Output changes as JSON lines"
        ),
    ):
        """Watch workspace for file changes and auto-evaluate compliance."""
        from datetime import datetime

        from aegis.domain.evaluation.service import EvaluationService
        from aegis.infrastructure.file_watcher import FileWatcher

        root = self.container.workspace_root
        rules = self.container.load_rules()
        if not rules:
            self.console.print("[red]Error: No rules found.[/red]")
            raise typer.Exit(code=1)

        if phase or category:
            from aegis.domain.policy.models import EvaluationPhase, RuleCategory
            phase_enum = EvaluationPhase(phase) if phase else None
            cat_enum = RuleCategory(category) if category else None
            rules = EvaluationService.filter_rules_by_phase(
                rules,
                phase=phase_enum,
                category=cat_enum,
                phase_mapping=self.container.category_phase_mapping,
            )

        if rule:
            rules = [r for r in rules if r.id == rule]
            if not rules:
                self.console.print(f"[red]Error: Rule '{rule}' not found.[/red]")
                raise typer.Exit(code=1)

        rules_map = {r.id: r for r in rules}
        bm = self.container.baseline_manager

        self.console.print(
            f"[bold blue]Aegis Watch[/bold blue] — monitoring {root}"
            f" ({len(rules)} rules, {interval}s interval)\n"
            "[dim]Press Ctrl+C to stop[/dim]"
        )

        def _on_change(added: set[str], modified: set[str], removed: set[str]) -> None:
            changed = (added | modified) - removed
            if not changed:
                return
            now = datetime.now().strftime("%H:%M:%S")
            for fp in sorted(changed):
                violations = self.container.evaluation_service.evaluate_file(fp, rules)
                active = (
                    [
                        v for v in violations
                        if not bm.is_exempt(v, rules_map.get(v.rule_id))
                    ]
                    if bm
                    else violations
                )
                if json_output:
                    event = {
                        "ts": now,
                        "file": fp,
                        "violations": [
                            {
                                "rule_id": v.rule_id,
                                "severity": str(v.severity),
                                "description": v.description,
                            }
                            for v in active
                        ],
                    }
                    self.console.print(json.dumps(event))
                elif active:
                    self.console.print(
                        f"[dim]{now}[/dim] [bold yellow]✗[/bold yellow] {fp}"
                        f" — [red]{len(active)} violation(s)[/red]"
                    )
                    for v in active:
                        self.console.print(
                            f"  [red]{v.severity}[/red] {v.rule_id}:"
                            f" {v.description} (line {v.line})"
                        )
                else:
                    self.console.print(
                        f"[dim]{now}[/dim] [green]✓[/green] {fp}"
                    )

        try:
            watcher = FileWatcher(root)
            watcher.watch(interval=interval, on_change=_on_change)
        except KeyboardInterrupt:
            self.console.print("\n[bold blue]Watch stopped.[/bold blue]")

    def self_check(self):
        """Enforces the self-governance invariant by auditing Aegis itself."""
        self.console.print("[bold blue]Aegis Self-Governance Audit[/bold blue]")
        try:
            self.check(staged=False, phase=None, rule=None, strict=False, category=None)
        except typer.Exit as e:
            if e.exit_code == 0:
                self.console.print(
                    "[bold green]PASS - Aegis is compliant"
                    " with its own laws.[/bold green]"
                )
            else:
                self.console.print(
                    "[bold red]FAIL - Self-governance violation detected![/bold red]"
                )
            raise e

    def run(self):
        self.app()

    @staticmethod
    def entry_point():

        # Route structlog to stderr so --json output on stdout stays clean
        try:
            import structlog

            structlog.configure(
                wrapper_class=structlog.stdlib.BoundLogger,
                logger_factory=structlog.PrintLoggerFactory(sys.stderr),
            )
        except ImportError:
            pass

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
