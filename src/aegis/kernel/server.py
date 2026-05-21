import json
import os
import re
from pathlib import Path

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
from aegis.domain.enforcement.ports import (
    RemediationResult,
)
from aegis.domain.enforcement.remediation import RemediationPromptSynthesizer
from aegis.infrastructure.graph_analyzer import GraphAnalyzer
from aegis.kernel.models import (
    AgentHandoffContext,
    CodeDeltaResult,
    ComplianceResult,
    DependencyGraphResult,
    PackInfo,
    RelevantRulesResult,
    RuleInfo,
    ServerStatusResult,
    ViolationInfo,
)

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

    @property
    def _telemetry_recorder(self):
        if self.container is not None:
            return self.container.telemetry_recorder
        return None

    def _register_tools(self):
        """
        Registers high-level Meta-Tools for AI agents.
        Consolidates 22 granular tools into 4 intent-driven facades.
        """
        self.mcp.tool()(self.plan_architecture)
        self.mcp.tool()(self.validate_workspace)
        self.mcp.tool()(self.evolve_ruleset)
        self.mcp.tool()(self.query_knowledge_graph)
        self.mcp.tool()(self.aegis_read_file)
        self.mcp.tool()(self.aegis_write_file)
        self.mcp.tool()(self.aegis_run_command)

    async def plan_architecture(
        self,
        intent: str | None = None,
        file_path: str | None = None,
        code_string: str | None = None,
        language: str = "py",
    ) -> str:
        """
        Meta-Tool: Pre-emptive task alignment and rule discovery.
        AI agents MUST call this at the START of a task or before editing a module.
        intent: Description of the coding task (e.g. 'Add a new domain service').
        file_path: Optional path to a specific file to get targeted rules.
        code_string: Optional code snippet to validate in-memory (mid-thought).
        language: Language of the code_string (defaults to 'py').
        """
        if code_string:
            # Innovation: Mid-thought validation via orphaned _evaluate_code_delta
            return await self._evaluate_code_delta(code_string, language)

        report = "# Aegis Architectural Alignment\n\n"

        if intent:
            steering = await self._propose_architectural_steering(intent)
            report += steering + "\n\n"

        if file_path:
            # Use the full _get_relevant_rules for comprehensive planning
            context = await self._get_relevant_rules(file_path)
            report += "## Targeted File Rules\n" + context + "\n"

        return report

    async def validate_workspace(
        self,
        scope: str = "full",
        phase: str | None = None,
        category: str | None = None,
        auto_fix: bool = False,
    ) -> str:
        """
        Meta-Tool: Comprehensive compliance gate and remediation engine.
        scope: 'full' (all files) or 'staged' (git staged changes only).
        phase: Optional filter by lifecycle phase (pre-commit, ci, etc.).
        category: Optional filter by rule category (security, architecture, etc.).
        auto_fix: If True, applies deterministic fixes before reporting.
        """
        if auto_fix:
            await self._apply_auto_fixes()

        compliance_json = await self._validate_architecture_compliance(
            staged_only=(scope == "staged"), phase=phase, category=category
        )

        # Parse the JSON string from internal method
        data = json.loads(compliance_json)
        if not data.get("passed"):
            remediation = await self._apply_architectural_remediation()
            # remediation is now a RemediationResult (pydantic)
            return compliance_json + "\n\n" + remediation.handoff_prompt

        return compliance_json

    async def evolve_ruleset(
        self,
        action: str,
        target: str | None = None,
        rationale: str | None = None,
        rules_yaml: str | None = None,
    ) -> str:
        """
        Meta-Tool: Manage the project's architectural laws and technical debt.
        action: 'init', 'auto_init', 'baseline', 'install_pack', 'remove_pack',
                'suppress', 'create_pack', 'test_rule'.
        target: Pack name, Rule ID, or Engine Type (for test_rule).
        rationale: Human reasoning for decisions.
        rules_yaml: YAML for creating/testing rules.
                   For 'test_rule', include 'pass' and 'fail' snippets.
        """
        if action == "init":
            return await self._initialize_project_governance()
        if action == "auto_init":
            return await self._autonomous_inference_initialization()
        if action == "baseline":
            return await self._capture_architectural_baseline()
        if action == "install_pack" and target:
            return await self._install_rule_pack(target)
        if action == "remove_pack" and target:
            return await self._remove_rule_pack(target)
        if action == "suppress" and target and rationale:
            return await self._negotiate_architectural_evolution(
                target, "suppress", rationale
            )
        if action == "create_pack" and target and rules_yaml:
            return await self._create_custom_pack(target, rules_yaml)
        if action == "test_rule" and target and rules_yaml:
            return await self._test_architectural_rule(target, rules_yaml)

        return f"ERROR: Unsupported or incomplete evolution action: {action}."

    async def query_knowledge_graph(
        self, query_type: str, target: str | None = None
    ) -> str:
        """
        Meta-Tool: Introspect project health, dependencies, and rule rationale.
        query_type: 'status', 'dependency', 'rationale', 'list_packs', 'dna'.
        target: Module name for dependency graph or Rule ID for rationale.
        """
        if query_type == "status":
            return await self._server_status()
        if query_type == "dependency" and target:
            return await self._get_dependency_graph(target)
        if query_type == "rationale" and target:
            return await self._get_rule_rationale(target)
        if query_type == "list_packs":
            return await self._list_rule_packs()
        if query_type == "dna":
            return await self._get_project_dna()

        return f"ERROR: Unsupported or incomplete knowledge query: {query_type}."

    async def aegis_read_file(self, path: str, session_id: str = "default") -> str:
        """
        Hardened Proxy: Reads file content and injects ambient micro-context.
        Ensures the agent is aware of the local laws without token bloat.
        """
        if self.container is None:
            return "ERROR: Kernel not initialized."

        try:
            # 1. Get raw content (respecting VFS if staged)
            content = self._evaluation_service._get_file_content(
                path, session_id=session_id
            )

            # 2. Get Governance DNA Micro-Context
            dna_raw = await self._get_active_context(path)
            dna = json.loads(dna_raw)

            # 3. Construct DNA Header (Micro-Context)
            # Instead of dumping full descriptions, we just list active rule IDs.
            # Full details are in aegis://dna which the agent has cached.
            header = f"# [AEGIS CONTEXT: {path}]\n"
            if dna.get("rules"):
                rule_ids = [r["id"] for r in dna["rules"]]
                header += f"# ACTIVE LAWS: {', '.join(rule_ids)}\n"
            else:
                header += "# ACTIVE LAWS: None\n"

            # Check quarantine status
            if self.container.vfs and self.container.vfs.is_quarantined(
                path, session_id=session_id
            ):
                header += (
                    "# [WARNING: FILE IS QUARANTINED. "
                    "FIX ARCHITECTURAL VIOLATIONS TO COMMIT.]\n"
                )

            header += "# ============================\n\n"

            return header + content
        except Exception as e:
            return f"ERROR: Failed to read file — {e}"

    async def aegis_write_file(
        self, path: str, content: str, session_id: str = "default"
    ) -> str:
        """
        Hardened Proxy: Speculative write with absolute enforcement.
        Quarantines the write if it violates high-severity architectural laws.
        """
        if self.container is None:
            return "ERROR: Kernel not initialized."

        vfs = self.container.vfs
        eval_service = self._evaluation_service

        if not vfs or not eval_service:
            return "ERROR: Governance Sandbox unavailable."

        # 1. Speculative Stage (In-Memory Only)
        vfs.stage_change(path, content, session_id=session_id)

        # 2. In-Flight Validation
        rules = self._load_rules()
        violations = eval_service.evaluate_file(
            path, rules, root_dir=self._workspace_root, session_id=session_id
        )

        # 3. Decision Gate
        # Only block on HIGH/CRITICAL violations
        blocking = [v for v in violations if v.severity in ("HIGH", "CRITICAL")]

        if blocking:
            # Quarantine: Do not commit, but keep in VFS.
            remediation = await self._apply_architectural_remediation()
            vfs.quarantine(path, remediation.handoff_prompt, session_id=session_id)
            return (
                f"QUARANTINED: Architectural Violation detected in {path}. "
                "The write operation is staged but BLOCKED from disk. "
                "You must apply the following specific diff to "
                "release the quarantine:\n\n"
                f"{remediation.handoff_prompt}"
            )

        # 4. Commit: Physically write to disk
        try:
            if vfs.commit(path, session_id=session_id):
                msg = f"SUCCESS: File {path} written securely."
                if violations:
                    msg += (
                        f"\n\nNOTE: {len(violations)} low-severity warnings surfaced."
                    )
                return msg
            return f"ERROR: Failed to commit {path} to disk."
        except Exception as e:
            return f"ERROR: Disk IO failure — {e}"

    async def aegis_run_command(self, command: str) -> str:
        """
        Safe Bash Execution Wrapper. Runs shell commands with post-execution 
        checks. If command introduces drift, changes are reverted via git.
        """
        import subprocess

        if self.container is None:
            return "ERROR: Kernel not initialized."

        try:
            # 1. Execute Command
            result = subprocess.run(
                command,
                shell=True,
                cwd=self._workspace_root,
                capture_output=True,
                text=True,
            )

            output = f"Command exited with {result.returncode}.\n"
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"

            # 2. Post-Execution Validation
            compliance_json = await self._validate_architecture_compliance(
                staged_only=False
            )
            data = json.loads(compliance_json)

            # 3. Rollback Mechanism
            if not data.get("passed"):
                # Rollback changes to tracked files via git
                subprocess.run(
                    ["git", "checkout", "--", "."],
                    cwd=self._workspace_root,
                    capture_output=True,
                )
                remediation = await self._apply_architectural_remediation()
                return (
                    f"{output}\n\n"
                    "ABORTED: The shell command introduced architectural drift. "
                    "All changes have been automatically REVERTED.\n"
                    "Refactor your approach to respect the invariants:\n\n"
                    f"{remediation.handoff_prompt}"
                )

            return (
                output
                + "\nSUCCESS: Command executed and architecture remains compliant."
            )
        except Exception as e:
            return f"ERROR: Failed to execute command — {e}"

    async def _propose_architectural_steering(self, task_description: str) -> str:
        """
        Creates an architectural flight plan for a task description.

        Uses keyword matching against rule descriptions to find relevant rules,
        then appends SPEC.md guidance and execution directives.
        This is a heuristic — for precise rule lookups use get_relevant_rules.
        Call at START of a task.
        """
        if self.container is None:
            return error(
                ERR_CONTAINER_NOT_INIT,
                "Kernel not initialized.",
                hint="Initialize the container first.",
            )

        spec = await self._get_architecture_spec()

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

    async def _get_relevant_rules(self, path: str) -> str:
        """
        Returns structured JSON of all rules applicable to a given file path.
        Call BEFORE editing a file to avoid violating project invariants.
        """
        if self.container is None:
            return error(
                ERR_CONTAINER_NOT_INIT,
                "Kernel not initialized.",
                hint="Initialize the container first.",
            )

        all_rules = self._load_rules()
        active_v_map = {}
        baseline_map = {}

        if self.container and self.container.governance_service:
            try:
                violations = self.container.governance_service.get_active_violations(
                    all_rules, self._workspace_root
                )
                for v in violations:
                    active_v_map[v.rule_id] = active_v_map.get(v.rule_id, 0) + 1
            except Exception:
                pass

        if self._baseline_manager:
            try:
                raw = self._baseline_manager.load_baseline_raw()
                for entry in raw:
                    rid = entry.get("rule_id")
                    if rid:
                        baseline_map[rid] = baseline_map.get(rid, 0) + 1
            except Exception:
                pass

        if not all_rules:
            return RelevantRulesResult(
                file_path=path,
                total_rules=0,
                rules=[],
                message="No rules found. Architecture is unconstrained.",
            ).model_dump_json()

        from aegis.domain.evaluation.scoping import ScopeFilter

        relevant = ScopeFilter.filter_rules_for_file(path, all_rules)

        rules_list = [
            RuleInfo(
                id=r.id,
                description=r.description,
                severity=r.severity.value,
                mode=r.mode.value,
                category=r.category.value,
                engine_type=r.engine_type.value,
                language=r.language,
                rationale=r.rationale,
                active_violations=active_v_map.get(r.id, 0),
                baseline_entries=baseline_map.get(r.id, 0),
            )
            for r in relevant
        ]

        result = RelevantRulesResult(
            file_path=path,
            total_rules=len(rules_list),
            rules=rules_list,
            message=(
                None
                if rules_list
                else f"No specific structural laws found for path: {path}."
            ),
        )
        return result.model_dump_json()

    async def _get_active_context(self, file_path: str) -> str:
        """
        Returns structured JSON of the 4-5 most relevant rules for a specific file.
        Uses path-based scoping and dependency graph proximity.
        Call before editing a file to understand applicable invariants.
        """
        if self.container is None:
            return error(
                ERR_CONTAINER_NOT_INIT,
                "Kernel not initialized.",
                hint="Initialize the container first.",
            )

        all_rules = self._load_rules()
        active_v_map = {}
        baseline_map = {}

        if self.container and self.container.governance_service:
            try:
                violations = self.container.governance_service.get_active_violations(
                    all_rules, self._workspace_root
                )
                for v in violations:
                    active_v_map[v.rule_id] = active_v_map.get(v.rule_id, 0) + 1
            except Exception:
                pass

        if self._baseline_manager:
            try:
                raw = self._baseline_manager.load_baseline_raw()
                for entry in raw:
                    rid = entry.get("rule_id")
                    if rid:
                        baseline_map[rid] = baseline_map.get(rid, 0) + 1
            except Exception:
                pass

        if not all_rules:
            return RelevantRulesResult(
                file_path=file_path,
                total_rules=0,
                rules=[],
                message="No rules found. Architecture is unconstrained.",
            ).model_dump_json()

        adjacency = None
        try:
            analyzer = self._graph_analyzer
            if analyzer is not None:
                adjacency, _ = analyzer.build_import_graph(self._workspace_root)
        except Exception:
            adjacency = None

        from aegis.domain.evaluation.scoping import ScopeFilter

        relevant = ScopeFilter.get_relevant_rules(
            file_path,
            all_rules,
            adjacency=adjacency,
            max_rules=5,
            base_dir=self._workspace_root,
        )

        rules_list = [
            RuleInfo(
                id=r.id,
                description=r.description,
                severity=r.severity.value,
                mode=r.mode.value,
                category=r.category.value,
                engine_type=r.engine_type.value,
                language=r.language,
                rationale=r.rationale,
                active_violations=active_v_map.get(r.id, 0),
                baseline_entries=baseline_map.get(r.id, 0),
            )
            for r in relevant
        ]

        result = RelevantRulesResult(
            file_path=file_path,
            total_rules=len(rules_list),
            rules=rules_list,
            message=(
                None if rules_list else f"No matching rules found for `{file_path}`."
            ),
        )
        return result.model_dump_json()

    async def _evaluate_code_delta(self, code_string: str, language: str) -> str:
        """
        Evaluates a code string in-memory against applicable rules.
        Returns structured JSON with violations and pass/fail status.
        Allows AI to validate mid-thought before writing to disk.
        """
        if not code_string or not language:
            return error(
                ERR_INVALID_INPUT,
                "code_string and language are required.",
            )

        all_rules = self._load_rules()
        if not all_rules:
            return error(
                ERR_NOT_INITIALIZED,
                "No rules loaded — run initialize_project_governance first.",
            )

        if self._evaluation_service is None:
            return error(
                ERR_SERVICE_UNAVAILABLE,
                "Evaluation service unavailable — container in degraded mode.",
            )

        violations = self._evaluation_service.evaluate_code_string(
            code_string, language, all_rules
        )

        violations_list = [
            ViolationInfo(
                file="<inline>",
                line=v.line,
                rule_id=v.rule_id,
                severity=v.severity,
                description=v.description,
            )
            for v in violations
        ]
        result = CodeDeltaResult(
            passed=len(violations) == 0,
            total_violations=len(violations),
            violations=violations_list,
        )
        return result.model_dump_json()

    async def _initialize_project_governance(self) -> str:
        """
        Bootstraps Aegis governance for the current repo.
        Creates .aegis/ directory, default rule packs, and config. Idempotent.
        """
        if self.container is None:
            return error(
                ERR_CONTAINER_NOT_INIT,
                "Kernel not initialized.",
                hint="Initialize the container first.",
            )

        from aegis.domain.governance.service import GovernanceService

        aegis_dir = GovernanceService.init_project_structure(self._workspace_root)
        rules_dir = os.path.join(aegis_dir or "", "rules")
        return (
            f"Aegis governance initialized at {aegis_dir}."
            f" Rules in {rules_dir}/. Use `/aegis-init` to customize."
        )

    async def _autonomous_inference_initialization(self) -> str:
        """
        Phase 2 Innovation: Zero-Config 'Lights Out' Initialization.
        Hypothesizes stack, installs relevant packs, and baselines all debt automatically.
        """
        if self.container is None:
            return error(ERR_CONTAINER_NOT_INIT, "Kernel not initialized.")

        # 1. Hypothesize
        hypothesis = await self._hypothesize_workspace_architecture()

        # 2. Init base structure
        from aegis.domain.governance.service import GovernanceService

        GovernanceService.init_project_structure(self._workspace_root)

        # 3. Extract recommendations from hypothesis and install them
        installed = []
        try:
            for line in hypothesis.splitlines():
                if line.startswith("**Recommended packs:**"):
                    packs_str = line.replace("**Recommended packs:**", "").strip()
                    if packs_str and packs_str != "None":
                        recommended_packs = [p.strip() for p in packs_str.split(", ")]
                        pm = self._rule_pack_manager
                        if pm:
                            for pack in recommended_packs:
                                try:
                                    pm.install(pack)
                                    installed.append(pack)
                                except ValueError:
                                    pass  # Already installed or invalid
        except Exception as e:
            self.logger.warning("Autonomous pack inference failed", error=str(e))

        # 4. Auto-Baseline
        baseline_msg = await self._capture_architectural_baseline()

        report = "# 🤖 Aegis Autonomous Initialization Complete\n\n"
        report += (
            "Aegis has successfully inferred your project structure and "
            "established governance.\n\n"
        )
        report += hypothesis + "\n\n"
        report += f"**Auto-Installed Packs:** {', '.join(installed) if installed else 'Default only'}\n"
        report += f"**Debt Ledger:** {baseline_msg}\n\n"
        report += "You are now running in an enforced Sandbox environment."

        return report

    async def _hypothesize_workspace_architecture(self) -> str:
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
            recommendations.extend(
                [
                    "python-best-practices",
                    "security",
                    "testing",
                    "structure",
                    "style",
                ]
            )
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

    async def _capture_architectural_baseline(self) -> str:
        """
        Captures current violations as baselined technical debt.
        Run after init so only NEW violations are reported.
        """
        if self.container is None:
            return error(
                ERR_CONTAINER_NOT_INIT,
                "Kernel not initialized.",
                hint="Initialize the container first.",
            )

        rules = self._load_rules()
        if not rules:
            return error(
                ERR_NOT_INITIALIZED,
                "Project not initialized. Call initialize_project_governance first.",
            )
        if not self.container.governance_service:
            return error(
                ERR_SERVICE_UNAVAILABLE,
                "Governance service unavailable — container in degraded mode.",
            )
        count = self.container.governance_service.capture_baseline(
            rules, self._workspace_root
        )
        return f"Successfully baselined {count} violations as legacy technical debt."

    async def _negotiate_architectural_evolution(
        self, rule_id: str, action: str, rationale: str
    ) -> str:
        """
        Records a consensus decision to evolve a rule.
        action: 'suppress' | 'relax_rule' | 'refactor_required'.
        suppress captures current violations to baseline.
        """
        if self.container is None:
            return error(
                ERR_CONTAINER_NOT_INIT,
                "Kernel not initialized.",
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

    async def _list_rule_packs(self) -> str:
        """
        Lists available, installed, and custom rule packs with descriptions.
        Returns structured JSON with separate installed/available/custom arrays.
        """
        pm = self._rule_pack_manager
        if pm is None:
            return error(ERR_SERVICE_UNAVAILABLE, "Rule pack manager unavailable.")

        available = pm.list_available()
        custom = pm.list_custom()
        installed_names = pm.list_installed()

        packs = [
            PackInfo(
                name=name,
                description=meta.description,
                installed=name in installed_names,
                version=meta.version,
            )
            for name, meta in available.items()
        ]
        custom_list = [{"name": name, "installed": True} for name in custom]

        return json.dumps(
            {
                "packs": [p.model_dump() for p in packs],
                "custom": custom_list,
                "summary": f"{len(installed_names)} installed, "
                f"{len(available)} available, {len(custom)} custom",
            },
            indent=2,
        )

    async def _install_rule_pack(self, pack_name: str) -> str:
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

    async def _remove_rule_pack(self, pack_name: str) -> str:
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

    async def _reset_rule_packs(self) -> str:
        """
        Removes all installed rule packs. Preserves custom root-level rule files.
        """
        pm = self._rule_pack_manager
        if pm is None:
            return error(ERR_SERVICE_UNAVAILABLE, "Rule pack manager unavailable.")

        pm.reset()
        return "All rule packs removed. Custom rules preserved."

    async def _create_custom_pack(self, pack_name: str, rules_yaml: str) -> str:
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

    async def _test_architectural_rule(self, engine_type: str, rules_yaml: str) -> str:
        """
        Innovation: Verifies a candidate rule against pass/fail snippets.
        AI agents should use this to iterate on Tree-sitter or Regex queries.
        rules_yaml should contain: query, language, pass_snippet, fail_snippet.
        """
        if self._evaluation_service is None:
            return error(ERR_SERVICE_UNAVAILABLE, "Evaluation service unavailable.")

        try:
            data = yaml.safe_load(rules_yaml)
            query = data.get("query")
            lang = data.get("language", "py")
            pass_snippet = data.get("pass_snippet", "")
            fail_snippet = data.get("fail_snippet", "")
        except yaml.YAMLError as e:
            return error(ERR_INVALID_INPUT, f"Invalid YAML — {e}")

        from aegis.domain.policy.models import (
            EnforcementMode,
            EngineType,
            Rule,
            Severity,
        )

        # Create temporary rule for testing
        test_rule = Rule(
            id="test-temp",
            description="Verification test",
            severity=Severity.LOW,
            mode=EnforcementMode.REPORT,
            engine_type=EngineType(engine_type),
            query=query,
            language=lang,
        )

        report = "# Aegis Rule Verification Report\n\n"

        # Test Pass Snippet
        pass_violations = self._evaluation_service.evaluate_code_string(
            pass_snippet, lang, [test_rule]
        )
        report += "### Test 1: Pass Snippet\n"
        if not pass_violations:
            report += "✅ SUCCESS: No violations detected (as expected).\n"
        else:
            report += (
                f"❌ FAILED: Detected {len(pass_violations)} unexpected violations.\n"
            )
            for v in pass_violations:
                report += f"  - Line {v.line}: {v.description}\n"

        # Test Fail Snippet
        fail_violations = self._evaluation_service.evaluate_code_string(
            fail_snippet, lang, [test_rule]
        )
        report += "\n### Test 2: Fail Snippet\n"
        if fail_violations:
            report += (
                f"✅ SUCCESS: Detected {len(fail_violations)} "
                "violations (as expected).\n"
            )
            for v in fail_violations:
                report += f"  - Line {v.line}: {v.description}\n"
        else:
            report += "❌ FAILED: No violations detected in snippet that should fail.\n"

        report += "\n**Conclusion:** "
        if not pass_violations and fail_violations:
            report += "Rule is VERIFIED. You can now codify it."
        else:
            report += "Rule needs REFINEMENT. The query does not match correctly."

        return report

    async def _apply_auto_fixes(self) -> str:
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

    async def _update_rule_packs(self, pack_name: str | None = None) -> str:
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

    async def _list_evaluation_phases(self) -> str:
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

    async def _get_phase_mapping(self) -> str:
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
                "Call the `plan_architecture` Meta-Tool with this description "
                "to get an Architectural Flight Plan. Before editing any file, "
                "call `plan_architecture(file_path=...)` to discover relevant "
                "rules. You can also call `plan_architecture(code_string=...)` "
                "to validate snippets mid-thought before writing to disk. "
                "Finally, read the `aegis://dna` resource to embed the highly "
                "compressed project manifesto into your context."
            )

        @self.mcp.prompt(
            name="evaluate-architecture",
            description="Scan workspace for compliance issues and build scorecard",
        )
        def evaluate_architecture_prompt() -> str:
            return (
                "You are an architectural governance auditor. "
                "Run `validate_architecture_compliance` on the full workspace. "
                "Returns structured JSON: passed (bool), violations[] with "
                "file, line, rule_id, severity, description for each violation. "
                "Parse the JSON directly — no string parsing needed. "
                "If violations are found, group them by rule_id and severity "
                "to produce a scorecard. "
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
                "Then call `validate_architecture_compliance` to see what remains "
                "(returns structured JSON with violations[]). "
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
            "aegis://context/{path}",
            description="Ambient Architectural Context for a specific file path",
        )
        async def get_path_context_resource(path: str) -> str:
            """
            Proactive Discovery: Returns relevant rules for a specific file.
            Agents can subscribe to this to receive ambient updates.
            """
            return await self._get_active_context(path)

        @self.mcp.resource(
            "aegis://dna",
            description="High-density token-compressed manifesto of project invariants",
        )
        async def get_dna_resource() -> str:
            return await self._get_project_dna()

        @self.mcp.resource(
            "aegis://rules",
            description="All active governance rules with queries, severity, and scope",
        )
        async def get_rules_resource() -> str:
            rules_dir = Path(self._workspace_root) / ".aegis" / "rules"
            rules_file = Path(self._workspace_root) / ".aegis" / "rules.yaml"

            if rules_dir.is_dir():
                parts = []
                for fp in sorted(rules_dir.rglob("*")):
                    if (
                        not fp.is_file()
                        or fp.suffix not in (".yaml", ".yml")
                        or fp.name == "pack.yaml"
                    ):
                        continue
                    rel = fp.relative_to(rules_dir)
                    try:
                        parts.append(
                            f"# --- {rel} ---\n{fp.read_text(encoding='utf-8')}"
                        )

                    except OSError as e:
                        parts.append(f"# --- {rel} ---\nERROR: {e}")
                return (
                    "\n\n".join(parts) if parts else warn("rules/ directory is empty.")
                )
            if rules_file.exists():
                try:
                    return rules_file.read_text(encoding="utf-8")
                except OSError as e:
                    return error(ERR_READ_FAILED, f"reading rules.yaml — {e}")
            return error(
                ERR_FILE_NOT_FOUND,
                "No rules found. Run `aegis init` to create governance rules.",
            )

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
                return warn(
                    "evolution_log.json not found — no evolution history recorded."
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
            "aegis://context",
            description="Compact governance state summary for agent-to-agent handoff",
        )
        async def get_context_resource() -> str:
            """
            Governance state snapshot for agent handoff.
            An agent finishing a governance task can read this and pass
            the summary to the next agent so it doesn't need to re-scan.
            """
            rules = self._load_rules()
            active: list = []
            baseline_count = 0
            if self._evaluation_service and self._baseline_manager:
                try:
                    active = self.container.governance_service.get_active_violations(
                        rules, self._workspace_root
                    )
                    raw = self._baseline_manager.load_baseline_raw()
                    baseline_count = len(raw)
                except Exception:
                    pass

            block_count = sum(1 for v in active if v.severity in ("HIGH", "CRITICAL"))
            top_rules = [
                RuleInfo(
                    id=r.id,
                    description=r.description,
                    severity=r.severity.value,
                    mode=r.mode.value,
                    category=r.category.value,
                    engine_type=r.engine_type.value,
                    language=r.language,
                    rationale=r.rationale,
                )
                for r in rules[:10]
            ]
            ctx = AgentHandoffContext(
                rules_loaded=len(rules),
                active_violations=len(active),
                blocking_violations=block_count,
                baselined_entries=baseline_count,
                top_rules=top_rules,
                status=(
                    "clean"
                    if not active
                    else "violations"
                    if block_count == 0
                    else "degraded"
                ),
                workspace=self._workspace_root,
            )
            return ctx.model_dump_json(indent=2)

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

    async def _get_architecture_spec(self) -> str:
        """Reads SPEC.md from the workspace root.

        Note: this reads an existing file, it does not generate one.
        Prefer the `aegis://spec` resource for cached access.
        Returns the file content or a WARN if not found."""
        try:
            spec_path = os.path.join(self._workspace_root, "SPEC.md")
            if not os.path.exists(spec_path):
                return warn("SPEC.md not found. Architecture is currently undefined.")
            with open(spec_path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.logger.error("Failed to read spec", error=str(e))
            return error(ERR_READ_FAILED, f"reading specification — {e}")

    async def _server_status(self) -> str:
        """
        Returns server health as structured JSON: version, container status,
        rule count, tool/resource/prompt counts, active violations, loaded plugins.
        """
        try:
            root = self._workspace_root
            rules = self._load_rules()
            active: list = []
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
            tm = getattr(self.mcp, "_tool_manager", None)
            tool_count = len(tm._tools) if tm and hasattr(tm, "_tools") else 21
            result = ServerStatusResult(
                version=_VERSION,
                status=container_status,
                workspace=root,
                rules_loaded=len(rules),
                tools_count=tool_count + plugin_tools,
                resources_count=6,
                prompts_count=6,
                active_violations=len(active),
                plugins_loaded=plugin_count,
            )
            return result.model_dump_json()
        except Exception as e:
            self.logger.error("Status check failed", error=str(e))
            return error(ERR_SERVICE_UNAVAILABLE, "status check failed", hint=str(e))

    async def _validate_architecture_compliance(
        self,
        staged_only: bool = False,
        phase: str | None = None,
        category: str | None = None,
    ) -> str:
        """
        Validates the workspace against all active rules.
        Returns structured JSON with violations, counts, and pass/fail status.
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
        rules_map = {r.id: r for r in rules}

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
                return error(
                    ERR_SERVICE_UNAVAILABLE,
                    "Evaluation service unavailable — container in degraded mode.",
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
                return error(
                    ERR_SERVICE_UNAVAILABLE,
                    "Governance service unavailable"
                    " — container running in degraded mode.",
                )
            active = self.container.governance_service.get_active_violations(
                rules, root
            )

        # Record telemetry
        if self._telemetry_recorder is not None:
            try:
                self._telemetry_recorder.record_check(len(active))
            except Exception:
                pass

        violations_list = [
            ViolationInfo(
                file=v.file,
                line=v.line,
                rule_id=v.rule_id,
                severity=v.severity,
                description=v.description,
                signature=v.signature,
                mode=rules_map.get(v.rule_id).mode.value
                if rules_map.get(v.rule_id)
                else "block",
            )
            for v in active
        ]
        blocking = [v for v in violations_list if v.severity in ("HIGH", "CRITICAL")]
        result = ComplianceResult(
            passed=len(active) == 0,
            message=(
                "Architecture compliance check passed. No new violations detected."
                if not active
                else f"{len(active)} active violations found."
            ),
            total_violations=len(active),
            blocking_violations=len(blocking),
            violations=violations_list,
        )
        return result.model_dump_json()

    async def _apply_architectural_remediation(self) -> RemediationResult:
        """
        Returns structured fix instructions for each active violation.
        Call after validate_architecture_compliance returns violations.
        For quick deterministic fixes, call apply_auto_fixes first.
        """
        if self.container is None:
            return RemediationResult(
                summary="Kernel not fully initialized.",
                violations_count=0,
                handoff_prompt=(
                    "ERROR: Kernel not fully initialized — container unavailable."
                ),
            )

        rules = self._load_rules()
        rules_map = {r.id: r for r in rules}
        if not self.container.governance_service:
            return RemediationResult(
                summary="Governance service unavailable.",
                violations_count=0,
                handoff_prompt=(
                    "ERROR: Governance service unavailable — "
                    "container in degraded mode."
                ),
            )
        active = self.container.governance_service.get_active_violations(
            rules, self._workspace_root
        )

        # Record telemetry for observability scorecard
        if self._telemetry_recorder is not None and active:
            try:
                for rid in {v.rule_id for v in active}:
                    self._telemetry_recorder.record_remediation(rid)
            except Exception:
                pass

        if not active:
            return RemediationResult(
                summary="Architecture is compliant.",
                violations_count=0,
                handoff_prompt=(
                    "PASS: Architecture is compliant. No remediation needed."
                ),
            )

        if self.remediation_synthesizer is None:
            return RemediationResult(
                summary="Remediation synthesizer unavailable.",
                violations_count=0,
                handoff_prompt="ERROR: Remediation synthesizer unavailable.",
            )

        return self.remediation_synthesizer.generate_remediation(active, rules_map)

    async def _get_rule_rationale(self, rule_id: str) -> str:
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

    async def _get_project_dna(self) -> str:
        """
        Returns a highly compressed, token-efficient 'Manifesto' of the project's invariants.
        This provides ambient architectural awareness for AI agents without token bloat.
        """
        all_rules = self._load_rules()
        if not all_rules:
            return "NO ARCHITECTURAL DNA FOUND."

        # Group rules by category for compression
        categories = {}
        for r in all_rules:
            if r.category.value not in categories:
                categories[r.category.value] = []
            categories[r.category.value].append(r)

        dna = "[AEGIS GOVERNANCE DNA]\n"
        for cat, rules in sorted(categories.items()):
            dna += f"[{cat.upper()}]\n"
            for r in rules:
                dna += (
                    f"- {r.id} ({r.severity.value}/{r.mode.value}): {r.description}\n"
                )

        return dna

    async def _get_dependency_graph(self, node_name: str) -> str:
        """
        Returns structured JSON of imports and reverse-dependencies for a module.
        Shows what the module imports, what imports it, and circular dependencies.
        """
        if not node_name or not node_name.strip():
            return error(ERR_INVALID_INPUT, "node_name must be a non-empty string.")

        if ".." in node_name or node_name.startswith("/") or node_name.startswith("\\"):
            return error(
                ERR_INVALID_INPUT,
                f"node_name '{node_name}' is not a valid module name.",
            )

        analyzer = self._graph_analyzer or GraphAnalyzer()
        adjacency, cycles = analyzer.build_import_graph(self._workspace_root)

        if not adjacency:
            return error(
                ERR_SERVICE_UNAVAILABLE,
                "No Python modules found or unable to parse dependency graph.",
            )

        matched = [m for m in adjacency if node_name in m]
        if not matched:
            return error(
                ERR_SERVICE_UNAVAILABLE,
                f"Module '{node_name}' not found in dependency graph.",
            )

        total_deps = 0
        total_rev_deps = 0
        for module in matched:
            total_deps += len(adjacency.get(module, set()))
            total_rev_deps += len(
                [m for m, deps in adjacency.items() if module in deps]
            )

        result = DependencyGraphResult(
            node_name=node_name,
            matched_modules=sorted(matched),
            total_dependencies=total_deps,
            total_reverse_dependencies=total_rev_deps,
            circular_dependency_count=len(cycles) if cycles else 0,
        )
        return result.model_dump_json()

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
        parser.add_argument(
            "--sandbox", action="store_true", help="Enable absolute enforcement sandbox"
        )
        args = parser.parse_args()

        kernel = AegisKernel()
        kernel.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    AegisKernel.entry_point()
