import os
import re

import structlog
import yaml
from mcp.server.fastmcp import FastMCP

from aegis.core.container.app import Container
from aegis.domain.enforcement.errors import (
    ERR_CONTAINER_NOT_INIT,
    ERR_FILE_NOT_FOUND,
    ERR_INVALID_INPUT,
    ERR_NOT_INITIALIZED,
    ERR_READ_FAILED,
    ERR_SERVICE_UNAVAILABLE,
    error,
    warn,
)
from aegis.domain.enforcement.remediation import RemediationPromptSynthesizer
from aegis.infrastructure.graph_analyzer import GraphAnalyzer

_VALID_TOOL_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_VERSION = "0.1.0"


def _named_tool(fn, name: str):
    """Wrap a function with a valid FastMCP tool name."""
    fn.__name__ = name
    fn.__qualname__ = name
    return fn


class AegisKernel:
    """
    The headless execution heart of Aegis.
    Acts as an MCP server providing architectural diagnostics to AI agents.
    """

    def __init__(self):
        self.logger = structlog.get_logger()
        self.mcp = FastMCP("Aegis Architecture Engine")
        self.container = self._init_container()
        self.remediation_synthesizer = self._init_remediation()
        self._plugin_tool_counter = 0
        self._register_tools()
        self._register_resources()
        self._register_prompts()
        self._register_plugin_tools()

    def _init_container(self):
        """Initialize the DI container with graceful degradation."""
        try:
            return Container()
        except Exception as e:
            self.logger.error("Container init failed", error=str(e))
            return None

    def _init_remediation(self):
        """Initialize remediation synthesizer with graceful degradation."""
        try:
            if self.container is not None and hasattr(
                self.container, "remediation_synthesizer"
            ):
                return self.container.remediation_synthesizer
            return RemediationPromptSynthesizer()
        except Exception as e:
            self.logger.error("Remediation init failed", error=str(e))
            return None

    @property
    def _workspace_root(self) -> str:
        """Safe workspace root accessor — returns CWD if container unavailable."""
        if self.container is not None:
            return self.container.workspace_root
        return os.getcwd()

    def _load_rules(self) -> list:
        """Load rules from the container."""
        if self.container is not None:
            return self.container.load_rules()
        return []

    @property
    def _policy_parser(self):
        if self.container is not None:
            return self.container.policy_parser
        return None

    @property
    def _evaluation_service(self):
        if self.container is not None:
            return self.container.evaluation_service
        return None

    @property
    def _baseline_manager(self):
        if self.container is not None:
            return self.container.baseline_manager
        return None

    @property
    def _evolution_service(self):
        if self.container is not None:
            return self.container.evolution_service
        return None

    @property
    def _graph_analyzer(self):
        if self.container is not None:
            return self.container.graph_analyzer
        return None

    def _register_tools(self):
        self.mcp.tool()(self.get_architecture_spec)
        self.mcp.tool()(self.validate_architecture_compliance)
        self.mcp.tool()(self.apply_architectural_remediation)
        self.mcp.tool()(self.get_rule_rationale)
        self.mcp.tool()(self.get_dependency_graph)
        self.mcp.tool()(self.server_status)
        self.mcp.tool()(self.initialize_project_governance)
        self.mcp.tool()(self.capture_architectural_baseline)
        self.mcp.tool()(self.negotiate_architectural_evolution)
        self.mcp.tool()(self.list_rule_packs)
        self.mcp.tool()(self.install_rule_pack)
        self.mcp.tool()(self.remove_rule_pack)
        self.mcp.tool()(self.reset_rule_packs)
        self.mcp.tool()(self.create_custom_pack)
        self.mcp.tool()(self.hypothesize_workspace_architecture)
        self.mcp.tool()(self.get_relevant_rules)
        self.mcp.tool()(self.propose_architectural_steering)
        self.mcp.tool()(self.apply_auto_fixes)
        self.mcp.tool()(self.update_rule_packs)
        self.mcp.tool()(self.list_evaluation_phases)
        self.mcp.tool()(self.get_phase_mapping)

    async def propose_architectural_steering(self, task_description: str) -> str:
        """
        Call at START of a task. Returns relevant rules, SPEC.md guidance,
        and execution directives for the given task description.
        """
        if self.container is None:
            return error(
                ERR_CONTAINER_NOT_INIT, "Kernel not initialized.",
                hint="Initialize the container first.",
            )

        # 1. Fetch relevant docs
        spec = await self.get_architecture_spec()

        # 2. Identify potential modules based on description
        # (Simple keyword matching for now, can be LLM-enhanced later)
        keywords = ["domain", "service", "adapter", "api", "model", "cli"]
        potential_paths = [kw for kw in keywords if kw in task_description.lower()]

        rules = self._load_rules()
        relevant_rules = []
        if potential_paths:
            from aegis.domain.evaluation.scoping import ScopeFilter

            for path in potential_paths:
                relevant_rules.extend(ScopeFilter.filter_rules_for_file(path, rules))

        # De-duplicate rules
        seen = set()
        unique_rules = []
        for r in relevant_rules:
            if r.id not in seen:
                unique_rules.append(r)
                seen.add(r.id)

        plan = "# Aegis Architectural Flight Plan\n\n"
        plan += f"**Task:** {task_description}\n\n"
        plan += "## Critical Invariants to Respect\n"
        if unique_rules:
            for r in unique_rules:
                plan += f"- **{r.id}**: {r.description}\n"
        else:
            plan += "- No high-specific structural rules detected.\n"

        plan += "\n## Project Guidelines\n"
        if "WARN: SPEC.md not found" not in spec:
            # Extract first 5 lines of spec as guidance
            lines = spec.splitlines()[:10]
            plan += "> " + "\n> ".join(lines) + "\n"
        else:
            plan += (
                "- Follow standard hexagonal/OOD"
                " principles established in the codebase.\n"
            )

        plan += "\n## Execution Directive\n"
        plan += "1. Ensure all new logic is encapsulated in appropriate layers.\n"
        plan += "2. Run `validate_architecture_compliance --staged-only` frequently.\n"
        plan += "3. If in doubt, query `get_rule_rationale` for existing laws."

        return plan

    async def get_relevant_rules(self, path: str) -> str:
        """
        Returns all architectural laws applicable to a given file path.
        Call BEFORE editing a file to avoid violating project invariants.
        """
        if self.container is None:
            return error(
                ERR_CONTAINER_NOT_INIT, "Kernel not initialized.",
                hint="Initialize the container first.",
            )

        all_rules = self._load_rules()
        if not all_rules:
            return "No rules found. Architecture is unconstrained."

        from aegis.domain.evaluation.scoping import ScopeFilter

        relevant = ScopeFilter.filter_rules_for_file(path, all_rules)

        if not relevant:
            return f"No specific structural laws found for path: {path}."

        report = f"## Active Laws for `{path}`\n\n"
        for r in relevant:
            report += f"### {r.id} ({r.severity})\n"
            report += f"- **Description:** {r.description}\n"
            if r.rationale:
                report += f"- **Rationale:** {r.rationale}\n"
            report += "\n"

        return report

    async def initialize_project_governance(self) -> str:
        """
        Bootstraps Aegis governance for the current repo.
        Creates .aegis/ directory, default rule packs, and config. Idempotent.
        """
        if self.container is None:
            return error(
                ERR_CONTAINER_NOT_INIT, "Kernel not initialized.",
                hint="Initialize the container first.",
            )

        from aegis.domain.governance.service import GovernanceService

        aegis_dir = GovernanceService.init_project_structure(self._workspace_root)
        rules_dir = os.path.join(aegis_dir or "", "rules")
        return (
            f"Aegis governance initialized at {aegis_dir}."
            f" Rules in {rules_dir}/. Use `/aegis-init` to customize."
        )

    async def hypothesize_workspace_architecture(self) -> str:
        """
        Scans the workspace to deduce the tech stack and C4 boundaries.
        Call silently at the start of init before talking to the user
        so the AI leads with data instead of asking questions.
        """
        root = self._workspace_root
        try:
            files = set(os.listdir(root))
        except OSError:
            files = set()

        # 1. Detect tech stack from standard markers
        stack = []
        markers = {
            "pyproject.toml": "Python",
            "requirements.txt": "Python",
            "Pipfile": "Python",
            "package.json": "Node.js/TypeScript",
            "yarn.lock": "Node.js/TypeScript",
            "Cargo.toml": "Rust",
            "go.mod": "Go",
            "go.sum": "Go",
            "Gemfile": "Ruby",
            "pom.xml": "Java",
            "build.gradle": "Java",
            "Dockerfile": "Docker",
            "docker-compose.yml": "Docker Compose",
            ".github/workflows/": "GitHub Actions",
        }
        for marker, label in markers.items():
            m_path = os.path.join(root, marker)
            if marker in files or (marker.endswith("/") and os.path.isdir(m_path)):
                if label not in stack:
                    stack.append(label)

        # 2. Detect architectural tiers using GraphAnalyzer
        bounded_contexts = []
        try:
            analyzer = self._graph_analyzer
            if analyzer is not None:
                adjacency, _ = analyzer.build_import_graph(root)
                if adjacency:
                    # Root-level packages = potential bounded contexts
                    seen = set()
                    for mod in adjacency:
                        top = mod.split(".")[0]
                        if top not in seen and top != "__init__":
                            seen.add(top)
                    bounded_contexts = sorted(seen)[:15]
        except Exception:
            bounded_contexts = []

        # 3. Build pack recommendations
        recommendations = []
        if "Python" in stack:
            recommendations.extend([
                "python-best-practices",
                "security",
                "testing",
                "structure",
                "style",
            ])
        if "Node.js/TypeScript" in stack:
            recommendations.append("javascript-typescript")
        if "Rust" in stack:
            recommendations.append("rust")
        if "Go" in stack:
            recommendations.append("go")
        if "Docker" in stack or "Docker Compose" in stack:
            recommendations.append("infrastructure")

        hypothesis_parts = []
        hypothesis_parts.append("# Workspace Architecture Hypothesis\n")
        stack_str = ", ".join(stack) if stack else "Unknown"
        hypothesis_parts.append(f"**Detected stack:** {stack_str}\n")
        if bounded_contexts:
            hypothesis_parts.append(
                f"**Detected bounded contexts:** `{'`, `'.join(bounded_contexts)}`\n"
            )
        rec_str = ", ".join(recommendations) if recommendations else "None"
        hypothesis_parts.append(f"**Recommended packs:** {rec_str}\n")
        if bounded_contexts:
            hypothesis_parts.append(
                "\n**Architecture insight:**"
                " The project has multiple root-level modules."
                " Consider enforcing layer isolation between them."
            )
        return "\n".join(hypothesis_parts)

    async def capture_architectural_baseline(self) -> str:
        """
        Captures current violations as baselined technical debt.
        Run after init so only NEW violations are reported.
        """
        if self.container is None:
            return error(
                ERR_CONTAINER_NOT_INIT, "Kernel not initialized.",
                hint="Initialize the container first.",
            )

        rules = self._load_rules()
        if not rules:
            return error(
                ERR_NOT_INITIALIZED,
                "Project not initialized. Call initialize_project_governance first.",
            )
        if not self.container.governance_service:
            return (
                error(ERR_SERVICE_UNAVAILABLE,
                      "Governance service unavailable — container in degraded mode.")
            )
        count = self.container.governance_service.capture_baseline(
            rules, self._workspace_root
        )
        return f"Successfully baselined {count} violations as legacy technical debt."

    async def negotiate_architectural_evolution(
        self, rule_id: str, action: str, rationale: str
    ) -> str:
        """
        Records a consensus decision to evolve a rule.
        action: 'suppress' | 'relax_rule' | 'refactor_required'.
        suppress captures current violations to baseline.
        """
        if self.container is None:
            return error(
                ERR_CONTAINER_NOT_INIT, "Kernel not initialized.",
                hint="Initialize the container first.",
            )

        from aegis.core.models.evolution import EvolutionDecision

        decision = EvolutionDecision(
            rule_id=rule_id, action=action, rationale=rationale
        )
        self._evolution_service.log_decision(decision)

        result = f"Evolution decision for '{rule_id}' recorded: {action}."

        if action == "suppress":
            rules = self._load_rules()
            target = [r for r in rules if r.id == rule_id]
            if target and self.container.governance_service:
                count = self.container.governance_service.capture_baseline(
                    target, self._workspace_root
                )
                result += f" Suppressed {count} violations to baseline."

        return result

    async def list_rule_packs(self) -> str:
        """
        Lists available, installed, and custom rule packs with descriptions.
        """
        pm = self._rule_pack_manager
        if pm is None:
            return error(ERR_SERVICE_UNAVAILABLE, "Rule pack manager unavailable.")

        installed = pm.list_installed()
        available = pm.list_available()
        custom = pm.list_custom()

        lines = []
        if available:
            lines.append("## Available Rule Packs\n")
            for name, meta in available.items():
                status = "[installed]" if name in installed else "[available]"
                lines.append(f"- **{name}** {status} — {meta.description}")
            lines.append("")
        if custom:
            lines.append("## Custom (Unpackaged) Rules\n")
            for f in custom:
                lines.append(f"- {f}")
            lines.append("")
        lines.append(
            f"**Summary:** {len(installed)} installed, "
            f"{len(available)} available, {len(custom)} custom"
        )
        return "\n".join(lines)

    async def install_rule_pack(self, pack_name: str) -> str:
        """
        Installs a rule pack from Aegis defaults into .aegis/rules/<pack>/.
        """
        pm = self._rule_pack_manager
        if pm is None:
            return error(ERR_SERVICE_UNAVAILABLE, "Rule pack manager unavailable.")

        try:
            pm.install(pack_name)
            return f"Installed '{pack_name}' rule pack successfully."
        except ValueError as e:
            return error(ERR_INVALID_INPUT, str(e))

    async def remove_rule_pack(self, pack_name: str) -> str:
        """
        Removes an installed rule pack and its manifest entry.
        """
        pm = self._rule_pack_manager
        if pm is None:
            return error(ERR_SERVICE_UNAVAILABLE, "Rule pack manager unavailable.")

        try:
            pm.remove(pack_name)
            return f"Removed '{pack_name}' rule pack successfully."
        except ValueError as e:
            return error(ERR_INVALID_INPUT, str(e))

    async def reset_rule_packs(self) -> str:
        """
        Removes all installed rule packs. Preserves custom root-level rule files.
        """
        pm = self._rule_pack_manager
        if pm is None:
            return error(ERR_SERVICE_UNAVAILABLE, "Rule pack manager unavailable.")

        pm.reset()
        return "All rule packs removed. Custom rules preserved."

    async def create_custom_pack(self, pack_name: str, rules_yaml: str) -> str:
        """
        Creates a custom rule pack from YAML rule definitions.
        rules_yaml must be a YAML list of rule objects (or a dict with a "rules" key).
        """
        pm = self._rule_pack_manager
        if pm is None:
            return error(ERR_SERVICE_UNAVAILABLE, "Rule pack manager unavailable.")

        try:
            data = yaml.safe_load(rules_yaml)
            rules = data if isinstance(data, list) else data.get("rules", [])
        except yaml.YAMLError as e:
            return error(ERR_INVALID_INPUT, f"Invalid YAML — {e}")

        if not isinstance(rules, list):
            return error(
                ERR_INVALID_INPUT,
                "rules_yaml must contain a list of rule definitions.",
            )

        try:
            path = pm.create(pack_name, rules)
            return f"Created custom pack '{pack_name}' at {path}."
        except ValueError as e:
            return error(ERR_READ_FAILED, str(e))

    async def apply_auto_fixes(self) -> str:
        """
        Applies deterministic auto-fixes to fixable violations.
        Supports: bare except blocks, print->logger, f-strings.
        Returns a summary of what was fixed and what failed.
        """
        from aegis.domain.enforcement.fixer import (
            apply_fixes,
            list_fixable_rule_ids,
        )

        rules = self._load_rules()
        if not rules:
            return error(
                ERR_NOT_INITIALIZED,
                "No rules loaded — run initialize_project_governance first.",
            )

        fixable_ids = list_fixable_rule_ids()
        fixable_rules = [r for r in rules if r.id in fixable_ids]
        if not fixable_rules:
            return "No fixable violations found."

        rule_map = {r.id: r for r in rules}
        if not self.container or not self.container.governance_service:
            return error(
                ERR_SERVICE_UNAVAILABLE,
                "Governance service unavailable — container in degraded mode.",
            )
        violations = self.container.governance_service.get_active_violations(
            fixable_rules, self._workspace_root
        )
        if not violations:
            return "No fixable violations found."

        results = apply_fixes(violations, rule_map)
        fixed = [r for r in results if r.fixed]
        failed = [r for r in results if not r.fixed]

        lines = ["## Auto-Fix Results\n"]
        if fixed:
            lines.append(f"**Fixed:** {len(fixed)} violations\n")
            for r in fixed:
                lines.append(f"- {r.file}:{r.line} ({r.rule_id})")
        if failed:
            lines.append(f"\n**Failed:** {len(failed)} violations\n")
            for r in failed:
                lines.append(f"- {r.file}:{r.line} — {r.message}")
        return "\n".join(lines) if (fixed or failed) else "No fixable violations found."

    async def update_rule_packs(self, pack_name: str | None = None) -> str:
        """
        Updates installed rule pack(s) to the latest defaults.
        Omit pack_name to update all installed packs.
        Preserves custom overrides within each pack.
        """
        pm = self._rule_pack_manager
        if pm is None:
            return error(ERR_SERVICE_UNAVAILABLE, "Rule pack manager unavailable.")

        updated = pm.update(pack_name)
        if updated:
            return f"Updated: {', '.join(updated)}"
        return "All packs are up-to-date."

    async def list_evaluation_phases(self) -> str:
        """
        Lists evaluation phases with rule counts for each phase.
        Useful for understanding when rules are evaluated.
        """
        rules = self._load_rules()
        if not rules:
            return error(
                ERR_NOT_INITIALIZED,
                "No rules loaded — run initialize_project_governance first.",
            )

        if self.container is None:
            return error(ERR_CONTAINER_NOT_INIT, "Container unavailable.")

        from aegis.domain.policy.models import EvaluationPhase

        phase_counts: dict[str, int] = {}
        mapping = self.container.category_phase_mapping

        for p in EvaluationPhase:
            filtered = [
                r
                for r in rules
                if r.phases is not None
                and p in r.phases
                or r.phases is None
                and p in mapping.category_defaults.get(r.category, [])
            ]
            phase_counts[p.value] = len(filtered)

        lines = ["## Evaluation Phases\n"]
        for phase_name in sorted(phase_counts.keys()):
            lines.append(f"- **{phase_name}:** {phase_counts[phase_name]} rules")
        return "\n".join(lines)

    async def get_phase_mapping(self) -> str:
        """
        Shows the current category-to-phase mapping.
        Each rule category maps to one or more evaluation phases.
        """
        if self.container is None:
            return error(ERR_CONTAINER_NOT_INIT, "Container unavailable.")

        mapping = self.container.category_phase_mapping
        lines = ["## Category -> Phase Mapping\n"]
        for cat, phases in sorted(mapping.category_defaults.items()):
            phase_str = ", ".join(p.value for p in phases)
            lines.append(f"- **{cat.value}:** {phase_str}")
        return "\n".join(lines)

    @property
    def _rule_pack_manager(self):
        if self.container is not None:
            return self.container.rule_pack_manager
        return None

    def _register_prompts(self):
        """Register reusable MCP prompts for development workflows."""

        @self.mcp.prompt(
            name="start-new-task",
            description="Start a new task with architectural context and rules",
        )
        def start_new_task_prompt(description: str) -> str:
            return (
                f"I am starting the following task: {description}. "
                "Call `propose_architectural_steering` with this description "
                "to get relevant rules and guidance. Then read the `aegis://rules` "
                "resource to align your implementation with project invariants."
            )

        @self.mcp.prompt(
            name="evaluate-architecture",
            description="Scan workspace for compliance issues and build scorecard",
        )
        def evaluate_architecture_prompt() -> str:
            return (
                "You are an architectural governance auditor. "
                "Run `validate_architecture_compliance` on the full workspace. "
                "If violations are found, group them by rule and severity, "
                "then produce a scorecard showing the worst offenders. "
                "Call `list_evaluation_phases` and `get_phase_mapping` to "
                "contextualize when each rule is evaluated."
            )

        @self.mcp.prompt(
            name="remediate-violations",
            description="Fix violations: auto-fix then manual step-by-step remediation",
        )
        def remediate_violations_prompt() -> str:
            return (
                "You are a remediation agent. First call `apply_auto_fixes` "
                "to resolve deterministic violations automatically. "
                "Then call `validate_architecture_compliance` to see what remains. "
                "For remaining violations, call `apply_architectural_remediation` "
                "for structured fix instructions, then resolve each violation "
                "one by one. Re-validate after each fix until all are cleared."
            )

        @self.mcp.prompt(
            name="explain-rule",
            description="Get the rationale and evolution history for a specific rule",
        )
        def explain_rule_prompt(rule_id: str) -> str:
            return (
                f"Call `get_rule_rationale` for rule '{rule_id}' to understand "
                "its purpose, evolution history, and any past decisions about it. "
                "Then read the rule definition from the `aegis://rules` resource. "
                "Summarize what the rule enforces, why it exists, and how it has "
                "evolved over time."
            )

        @self.mcp.prompt(
            name="initialize-governance",
            description="Initialize Aegis governance with auto-detection and baseline",
        )
        def initialize_governance_prompt() -> str:
            return (
                "You are setting up architectural governance. "
                "First call `hypothesize_workspace_architecture` to detect"
                " the tech stack and bounded contexts. "
                "Present the findings to the user and suggest relevant rule packs. "
                "If they agree, call `initialize_project_governance`, "
                "then `install_rule_pack` for each recommended pack. "
                "Finally call `capture_architectural_baseline` to mark"
                " existing violations as accepted debt."
            )

        @self.mcp.prompt(
            name="inspect-dependency",
            description="Analyze module dependencies and coupling in the workspace",
        )
        def inspect_dependency_prompt(node_name: str) -> str:
            return (
                f"Call `get_dependency_graph` for module '{node_name}' to inspect "
                "its imports and reverse-dependencies. Check for: (1) circular "
                "dependencies, (2) domain->infrastructure leaks, (3) excessive "
                "coupling. Report findings and suggest refactoring if needed."
            )

    def _register_resources(self):
        """Register static governance artifacts as MCP resources."""

        @self.mcp.resource(
            "aegis://rules",
            description="All active governance rules with queries, severity, and scope",
        )
        async def get_rules_resource() -> str:
            rules_dir = os.path.join(self._workspace_root, ".aegis", "rules")
            rules_file = os.path.join(self._workspace_root, ".aegis", "rules.yaml")

            if os.path.isdir(rules_dir):
                parts = []
                for root, _dirs, files in os.walk(rules_dir):
                    for f in sorted(files):
                        if not f.endswith((".yaml", ".yml")) or f == "pack.yaml":
                            continue
                        fp = os.path.join(root, f)
                        rel = os.path.relpath(fp, rules_dir)
                        try:
                            with open(fp, encoding="utf-8") as fh:
                                parts.append(f"# --- {rel} ---\n{fh.read()}")
                        except OSError as e:
                            parts.append(f"# --- {rel} ---\nERROR: {e}")
                return (
                    "\n\n".join(parts) if parts else warn("rules/ directory is empty.")
                )
            if os.path.exists(rules_file):
                try:
                    with open(rules_file, encoding="utf-8") as f:
                        return f.read()
                except OSError as e:
                    return error(ERR_READ_FAILED, f"reading rules.yaml — {e}")
            return error(ERR_FILE_NOT_FOUND,
                         "No rules found. Run `aegis init` to create governance rules.")

        @self.mcp.resource(
            "aegis://baseline",
            description="Known technical debt exempted from active reporting",
        )
        async def get_baseline_resource() -> str:
            path = os.path.join(self._workspace_root, ".aegis", "baseline.json")
            if not os.path.exists(path):
                return warn("baseline.json not found — no debt ledger established.")
            try:
                with open(path, encoding="utf-8") as f:
                    return f.read()
            except OSError as e:
                self.logger.error(
                    "Failed to read baseline resource", path=path, error=str(e)
                )
                return error(ERR_READ_FAILED, f"reading baseline.json — {e}")

        @self.mcp.resource(
            "aegis://evolution",
            description="Logged rule evolution decisions with timestamps",
        )
        async def get_evolution_resource() -> str:
            path = os.path.join(self._workspace_root, ".aegis", "evolution_log.json")
            if not os.path.exists(path):
                return (
                    warn("evolution_log.json not found"
                         " — no evolution history recorded.")
                )
            try:
                with open(path, encoding="utf-8") as f:
                    return f.read()
            except OSError as e:
                self.logger.error(
                    "Failed to read evolution resource", path=path, error=str(e)
                )
                return error(ERR_READ_FAILED, f"reading evolution_log.json — {e}")

        @self.mcp.resource(
            "aegis://spec", description="Architecture specification (SPEC.md)"
        )
        async def get_spec_resource() -> str:
            path = os.path.join(self._workspace_root, "SPEC.md")
            if not os.path.exists(path):
                return warn("SPEC.md not found — architecture is undefined.")
            try:
                with open(path, encoding="utf-8") as f:
                    return f.read()
            except OSError as e:
                self.logger.error(
                    "Failed to read spec resource", path=path, error=str(e)
                )
                return error(ERR_READ_FAILED, f"reading SPEC.md — {e}")

    def _register_plugin_tools(self):
        if self.container is None:
            self.logger.warning(
                "Container unavailable — skipping plugin tool registration"
            )
            return
        for tool_fn in self.container.custom_mcp_tools:
            name = getattr(tool_fn, "__name__", "") or ""
            if not name or not _VALID_TOOL_NAME.match(name):
                name = f"plugin_tool_{self._plugin_tool_counter}"
                self._plugin_tool_counter += 1
                wrapper = _named_tool(tool_fn, name)
                self.mcp.tool(name=name)(wrapper)
            else:
                self.mcp.tool()(tool_fn)
            self.logger.info("Registered custom MCP tool", tool=name)

    async def get_architecture_spec(self) -> str:
        """Returns the project's SPEC.md content, or a WARN if not found."""
        try:
            spec_path = os.path.join(self._workspace_root, "SPEC.md")
            if not os.path.exists(spec_path):
                return warn("SPEC.md not found. Architecture is currently undefined.")
            with open(spec_path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.logger.error("Failed to read spec", error=str(e))
            return error(ERR_READ_FAILED, f"reading specification — {e}")

    async def server_status(self) -> str:
        """
        Returns server health: version, container status, rule count,
        tool/resource/prompt counts, active violations, loaded plugins.
        """
        try:
            root = self._workspace_root
            rules = self._load_rules()
            active = []
            plugin_count = 0
            plugin_tools = 0
            if self._evaluation_service and self._baseline_manager:
                active = self.container.governance_service.get_active_violations(
                    rules, root
                )
            if self.container is not None:
                plugin_tools = len(self.container.custom_mcp_tools)
                plugin_count = len(self.container.loaded_plugins)

            container_status = "degraded" if self.container is None else "ready"
            summary = "## Aegis Kernel Status\n\n"
            summary += f"- **Version:** {_VERSION}\n"
            summary += f"- **Status:** {container_status}\n"
            summary += f"- **Workspace:** `{root}`\n"
            summary += f"- **Rules:** {len(rules)} loaded\n"
            tm = getattr(self.mcp, '_tool_manager', None)
            tool_count = len(tm._tools) if tm and hasattr(tm, '_tools') else 21
            summary += f"- **Tools:** {tool_count} built-in + {plugin_tools} plugin\n"
            summary += "- **Resources:** 4 governance artifacts\n"
            summary += "- **Prompts:** 5 workflow templates\n"
            summary += f"- **Violations:** {len(active)} active\n"
            summary += f"- **Plugins:** {plugin_count} loaded\n"
            return summary
        except Exception as e:
            self.logger.error("Status check failed", error=str(e))
            return error(ERR_SERVICE_UNAVAILABLE, "status check failed", hint=str(e))

    async def validate_architecture_compliance(
        self,
        staged_only: bool = False,
        phase: str | None = None,
        category: str | None = None,
    ) -> str:
        """
        Validates the workspace against all active rules.
        Returns PASS or a list of violations with file, line, severity, and rule ID.
        staged_only: only check git-staged changes.
        phase: filter by 'pre-commit'|'pre-push'|'ci'|'nightly'|'on-demand'.
        category: filter by rule category.
        """
        if self.container is None:
            return error(
                ERR_CONTAINER_NOT_INIT,
                "Kernel not fully initialized — container unavailable.",
            )

        root = self._workspace_root
        rules = self._load_rules()

        if phase or category:
            from aegis.domain.evaluation.service import EvaluationService
            from aegis.domain.policy.models import EvaluationPhase, RuleCategory

            phase_enum = EvaluationPhase(phase) if phase else None
            cat_enum = RuleCategory(category) if category else None
            rules = EvaluationService.filter_rules_by_phase(
                rules,
                phase=phase_enum,
                category=cat_enum,
                phase_mapping=self.container.category_phase_mapping,
            )
        if not rules:
            return error(
                ERR_NOT_INITIALIZED,
                "Aegis is not initialized — run initialize_project_governance first.",
            )

        if staged_only:
            if not self._evaluation_service:
                return (
                    error(ERR_SERVICE_UNAVAILABLE,
                          "Evaluation service unavailable"
                      " — container in degraded mode.")
                )
            violations = self._evaluation_service.evaluate_changes(rules, root_dir=root)
            rules_map = {r.id: r for r in rules}
            bm = self._baseline_manager
            active = (
                [v for v in violations if not bm.is_exempt(v, rules_map.get(v.rule_id))]
                if bm
                else violations
            )
        else:
            if not self.container.governance_service:
                return (
                    error(ERR_SERVICE_UNAVAILABLE,
                          "Governance service unavailable"
                          " — container running in degraded mode.")
                )
            active = self.container.governance_service.get_active_violations(
                rules, root
            )

        if not active:
            return (
                "PASS: Architecture compliance check passed."
                " No new violations detected."
            )

        report = "FAIL: ARCHITECTURAL DRIFT DETECTED\n"
        report += "The following NEW violations must be resolved before proceeding:\n\n"
        for v in active:
            report += f"- [{v.severity}] {v.file}:{v.line}\n"
            report += f"  Violation: {v.description} ({v.rule_id})\n"

        report += (
            "\nUse the `apply_architectural_remediation` tool "
            "to receive specific refactoring instructions."
        )
        return report

    async def apply_architectural_remediation(self) -> str:
        """
        Returns structured fix instructions for each active violation.
        Call after validate_architecture_compliance returns violations.
        For quick deterministic fixes, call apply_auto_fixes first.
        """
        if self.container is None:
            return error(
                ERR_CONTAINER_NOT_INIT,
                "Kernel not fully initialized — container unavailable.",
            )

        rules = self._load_rules()
        rules_map = {r.id: r for r in rules}
        if not self.container.governance_service:
            return (
                error(ERR_SERVICE_UNAVAILABLE,
                      "Governance service unavailable — container in degraded mode.")
            )
        active = self.container.governance_service.get_active_violations(
            rules, self._workspace_root
        )

        if not active:
            return "PASS: Architecture is compliant. No remediation needed."

        if self.remediation_synthesizer is None:
            return error(
                ERR_SERVICE_UNAVAILABLE, "Remediation synthesizer unavailable."
            )

        return self.remediation_synthesizer.generate_remediation(active, rules_map)

    async def get_rule_rationale(self, rule_id: str) -> str:
        """
        Returns the rule's description, rationale, severity, and evolution history.
        """
        if not rule_id or not rule_id.strip():
            return error(ERR_INVALID_INPUT, "rule_id must be a non-empty string.")

        if not re.match(r"^[a-zA-Z0-9_-]+$", rule_id):
            return error(
                ERR_INVALID_INPUT,
                f"rule_id '{rule_id}' contains invalid characters.",
            )

        all_rules = self._load_rules()
        rule = next((r for r in all_rules if r.id == rule_id), None)

        if not rule:
            return warn(f"rule '{rule_id}' not found in the governance matrix.")

        result = f"## Rule: {rule.id}\n"
        result += f"**Description:** {rule.description}\n"
        result += f"**Engine:** {rule.engine_type.value}\n"
        result += f"**Mode:** {rule.mode.value}\n"
        result += f"**Severity:** {rule.severity.value}\n"
        if rule.rationale:
            result += f"**Rationale:** {rule.rationale}\n"

        if self._evolution_service:
            log = self._evolution_service.load_log()
        else:
            log = None

        decisions = [d for d in log.decisions if d.rule_id == rule_id] if log else []

        if decisions:
            result += "\n### Evolution History\n"
            for d in decisions:
                result += f"- **{d.timestamp}** — {d.action}: {d.rationale}\n"
        else:
            result += "\nNo evolution history recorded for this rule."

        return result

    async def get_dependency_graph(self, node_name: str) -> str:
        """
        Returns imports and reverse-dependencies for a given module name.
        Shows what the module imports and what imports it.
        """
        if not node_name or not node_name.strip():
            return error(ERR_INVALID_INPUT, "node_name must be a non-empty string.")

        # Prevent path traversal in module name
        if ".." in node_name or node_name.startswith("/") or node_name.startswith("\\"):
            return error(
                ERR_INVALID_INPUT,
                f"node_name '{node_name}' is not a valid module name.",
            )

        # Build the full dependency graph
        analyzer = self._graph_analyzer or GraphAnalyzer()
        adjacency, _ = analyzer.build_import_graph(self._workspace_root)

        if not adjacency:
            return (
                warn("no Python modules found in the workspace "
                     "or unable to parse dependency graph.")
            )

        # Find the requested node (fuzzy match: any node containing the name)
        matched = [m for m in adjacency if node_name in m]

        if not matched:
            return (
                warn(f"module '{node_name}' not found in the dependency graph.\n"
                     f"Available roots: {', '.join(sorted(adjacency.keys())[:10])}")
            )

        result = f"## Dependency Graph: `{node_name}`\n\n"

        for module in sorted(matched):
            result += f"### {module}\n"
            deps = adjacency.get(module, set())
            if deps:
                result += "**Imports:**\n"
                for d in sorted(deps):
                    result += f"- `{d}`\n"
            else:
                result += "No internal imports.\n"

            # Find reverse dependencies
            importers = [m for m, deps in adjacency.items() if module in deps]
            if importers:
                result += "**Imported by:**\n"
                for imp in sorted(importers):
                    result += f"- `{imp}`\n"

            result += "\n"

        return result

    def run(
        self,
        transport: str = "stdio",
        host: str = "127.0.0.1",
        port: int = 8000,
        cors_origins: str | None = None,
    ):
        """
        Runs the MCP server with the given transport.

        Args:
            transport: One of "stdio", "sse", or "streamable-http".
            host: Host to bind (SSE/HTTP only).
            port: Port to bind (SSE/HTTP only).
            cors_origins: Comma-separated CORS origins (SSE/HTTP only).
        """
        if transport == "stdio":
            self.mcp.run()
        elif transport in ("sse", "streamable-http"):
            import uvicorn

            app = (
                self.mcp.sse_app()
                if transport == "sse"
                else self.mcp.streamable_http_app()
            )

            if cors_origins:
                from starlette.middleware.cors import CORSMiddleware

                origins = [o.strip() for o in cors_origins.split(",")]
                app = CORSMiddleware(
                    app,
                    allow_origins=origins,
                    allow_methods=["GET", "POST", "OPTIONS"],
                    allow_headers=["*"],
                )

            uvicorn.run(app, host=host, port=port, log_level="warning")
        else:
            raise ValueError(f"Unsupported transport: {transport}")

    @staticmethod
    def entry_point():
        import argparse
        import sys

        # Route structlog to stderr so MCP JSON-RPC on stdout stays clean
        try:
            import structlog

            structlog.configure(
                wrapper_class=structlog.stdlib.BoundLogger,
                logger_factory=structlog.PrintLoggerFactory(sys.stderr),
            )
        except ImportError:
            pass

        parser = argparse.ArgumentParser(description="Aegis Architecture Engine (MCP)")
        parser.add_argument(
            "--transport",
            choices=["stdio", "sse", "streamable-http"],
            default="stdio",
            help="MCP transport protocol (default: stdio)",
        )
        parser.add_argument("--host", default="127.0.0.1", help="Bind host (SSE/HTTP)")
        parser.add_argument(
            "--port", type=int, default=8000, help="Bind port (SSE/HTTP)"
        )
        args = parser.parse_args()

        kernel = AegisKernel()
        kernel.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    AegisKernel.entry_point()
