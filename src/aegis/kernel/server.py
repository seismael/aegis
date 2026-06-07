import json
import os
import re
from datetime import datetime
from pathlib import Path

import structlog
from mcp.server.fastmcp import FastMCP

from aegis.domain.evaluation.analyzers.ast import TreeSitterAnalyzer
from aegis.domain.evaluation.analyzers.graph import GraphAnalyzer
from aegis.domain.evaluation.analyzers.regex import RegexAnalyzer
from aegis.domain.evaluation.analyzers.semantic import SemanticAnalyzer
from aegis.domain.evaluation.baseline import BaselineManager
from aegis.domain.evaluation.prompt_synthesizer import RemediationPromptSynthesizer
from aegis.domain.evaluation.scoping import ScopeFilter
from aegis.domain.evaluation.scorecard import Scorecard
from aegis.domain.evaluation.service import EvaluationService
from aegis.domain.evaluation.session import SessionManager
from aegis.domain.observability.telemetry import TelemetryRecorder
from aegis.domain.policy.pack_manager import RulePackManager
from aegis.domain.policy.parser import PolicyParser
from aegis.kernel.errors import (
    ERR_INVALID_INPUT,
    ERR_SERVICE_UNAVAILABLE,
    error,
    warn,
)
from aegis.kernel.models import DiscoveryResult, Proposal

_VERSION = "0.4.0"


class AegisKernel:
    """
    V4 Agent-Native Microkernel.
    Headless MCP server providing 10 tools for architectural governance.
    Every dependency is constructor-injected — no DI container.
    """

    def __init__(
        self,
        workspace_root: str | None = None,
    ):
        self.logger = structlog.get_logger()
        self._workspace_root = workspace_root or self._discover_root()
        self.session = SessionManager(self._workspace_root)

        try:
            from aegis.domain.evaluation.plugins.registry import PluginRegistry
            self.plugin_registry = PluginRegistry(self._workspace_root)
            self.plugin_registry.load_plugins()
        except Exception as e:
            self.logger.warning(f"Failed to load plugins: {e}")
            self.plugin_registry = None

        try:
            self.policy = PolicyParser(self._workspace_root)
        except Exception:
            self.policy = None
        try:
            self.regex = RegexAnalyzer()
            self.tree_sitter = TreeSitterAnalyzer()
            self.graph = GraphAnalyzer()
            self.semantic = SemanticAnalyzer()
            extra_analyzers = []
            if hasattr(self, "plugin_registry") and self.plugin_registry:
                extra_analyzers.extend(self.plugin_registry.custom_analyzers)
                
            self.evaluation = EvaluationService(
                tree_sitter_analyzer=self.tree_sitter,
                graph_analyzer=self.graph,
                regex_analyzer=self.regex,
                semantic_analyzer=self.semantic,
                extra_analyzers=extra_analyzers,
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize evaluation engine: {e}")
            self.regex = self.tree_sitter = None
            self.graph = self.semantic = self.evaluation = None
            self.evaluation = None
        try:
            self.baseline = BaselineManager(
                os.path.join(self._workspace_root, ".aegis")
            )
        except Exception:
            self.baseline = None
        try:
            self.packs = RulePackManager(
                os.path.join(self._workspace_root, ".aegis", "rules")
            )
        except Exception:
            self.packs = None
        try:
            self.telemetry = TelemetryRecorder(self._workspace_root)
        except Exception:
            self.telemetry = None
        try:
            self.scorecard = Scorecard(self._workspace_root)
        except Exception:
            self.scorecard = None
        try:
            self.remediation = RemediationPromptSynthesizer()
        except Exception:
            self.remediation = None

        self._adjacency_cache_entry: tuple[float, dict] | None = None

        self.mcp = FastMCP("Aegis Architecture Engine")
        
        if self._is_governed():
            self._register_tools()
            try:
                self._register_resources()
                self._register_prompts()
            except AttributeError:
                pass

    def _is_governed(self) -> bool:
        return (Path(self.workspace_root) / ".aegis").exists()

    @property
    def workspace_root(self) -> str:
        return self._workspace_root

    def _discover_root(self) -> str:
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
                return str(parent)
        return str(current)

    def _register_tools(self):
        self.mcp.tool()(self.check_architecture)
        self.mcp.tool()(self.fetch_rubric)
        self.mcp.tool()(self.init_governance)
        self.mcp.tool()(self.query_graph)
        self.mcp.tool()(self.manage_rules)
        self.mcp.tool()(self.plan_architecture)
        self.mcp.tool()(self.find_patterns)
        self.mcp.tool()(self.apply_rules)
        self.mcp.tool()(self.request_exception)
        self.mcp.tool()(self.get_scorecard)

    async def request_exception(
        self,
        rule_id: str,
        reason: str,
        file_path: str | None = None,
    ) -> str:
        """
        Petitions for an architectural exception.
        Records the technical debt and suppresses the violation for this session.
        """
        # Logic:
        # 1. Use BaselineManager to mark this rule as exempt.
        # 2. For simplicity, we reuse '_evolve_suppress'
        # 3. Update the Session for the handoff note

        result = await self._evolve_suppress(rule_id)
        if "SUCCESS" in result:
            state = self.session.load()
            note = f"EXCEPTION GRANTED: {rule_id} because {reason}"
            if state.handoff_notes:
                state.handoff_notes += f"\n{note}"
            else:
                state.handoff_notes = note
            self.session.save(state)
            return f"SUCCESS: Exception granted for '{rule_id}'. Reason: {reason}"

        return result

    async def get_scorecard(self) -> str:
        """
        (Re)generates the .aegis/AEGIS.md dashboard for agent/human visibility.
        Calculates health score and lists active rules.
        """
        if not self.scorecard:
            return error(ERR_SERVICE_UNAVAILABLE, "Scorecard service not initialized.")

        rules = self._load_rules()
        if not rules:
            return warn("No rules loaded. Run /aegis-init first.")

        if self.evaluation is None:
            return error(ERR_SERVICE_UNAVAILABLE, "Evaluation engine not initialized.")

        # Full workspace evaluation for health scorecard
        violations = self.evaluation.evaluate_workspace(self.workspace_root, rules)

        exceptions = []
        if self.baseline:
            exceptions = [e.get("rule_id") for e in self.baseline.load_baseline_raw()]

        content = self.scorecard.generate(rules, violations, exceptions)
        self.scorecard.sync_to_disk(content)

        return f"SUCCESS: AEGIS.md generated in {self.workspace_root}/.aegis."

    async def check_architecture(
        self,
        files_modified: list[str],
        phase: str = "pre-commit",
        execution_depth: int = 0,
        handoff_note: str | None = None,
    ) -> str:
        """
        JIT Compliance Gate. Call before declaring any task complete.
        Returns SUCCESS string or formatted violation report with remediation.
        """
        # Session Coordination Logic
        state = self.session.load()
        current_agent = self._get_agent_id()
        coordination_info = ""

        if state.handoff_notes or (
            state.last_validation_time and state.last_agent_id != current_agent
        ):
            coordination_info = "\n\n### 🤝 Coordination Info\n"
            if state.last_agent_id and state.last_agent_id != current_agent:
                coordination_info += f"- Last validated by: **{state.last_agent_id}**"
                if state.last_validation_time:
                    coordination_info += f" at {state.last_validation_time.isoformat()}"
                coordination_info += "\n"
            if state.handoff_notes:
                coordination_info += f"- Handoff Notes: {state.handoff_notes}\n"

        # Update and save session
        state.last_validation_time = datetime.now()
        state.last_agent_id = current_agent
        if handoff_note:
            state.handoff_notes = handoff_note
        self.session.save(state)

        if execution_depth > 3:
            return (
                warn(
                    f"BYPASS: Execution depth {execution_depth} exceeds limit (3). "
                    "Remaining violations will not block task completion. "
                    "Flag the following rules for manual architectural review."
                )
                + coordination_info
            )

        rules = self._load_rules()
        if not rules:
            return warn("No rules loaded. Run /aegis-init first.")

        phase_enum = None
        if phase != "pre-commit":
            try:
                from aegis.domain.policy.models import EngineType, EvaluationPhase

                phase_enum = EvaluationPhase(phase)
            except ValueError:
                return warn(
                    f"Unknown phase '{phase}'. "
                    "Valid phases: pre-commit, ci, nightly, on-demand."
                )
        else:
            from aegis.domain.policy.models import EngineType

        filtered = self._filter_rules_for_files(files_modified, rules)

        if self.evaluation is None:
            return error(
                ERR_SERVICE_UNAVAILABLE,
                "Evaluation engine not initialized. Check tree-sitter installation.",
            )
        if self.baseline is None:
            return error(
                ERR_SERVICE_UNAVAILABLE,
                "Baseline manager not initialized.",
            )

        rule_map = {r.id: r for r in rules}
        violations = self.evaluation.evaluate_workspace(
            self.workspace_root, filtered, phase=phase_enum
        )

        active = [
            v
            for v in violations
            if not self.baseline.is_exempt(v, rule_map.get(v.rule_id))
        ]

        # Semantic Rubric Generation
        semantic_rubrics = []
        semantic_rules = [r for r in filtered if r.engine_type == EngineType.SEMANTIC]
        if semantic_rules and self.semantic:
            for file_path in files_modified:
                scoped_semantic = ScopeFilter.filter_rules_for_file(
                    file_path, semantic_rules, rules
                )
                if scoped_semantic:
                    rubric = self.semantic.build_rubric(file_path, scoped_semantic)
                    semantic_rubrics.append(rubric)

        remediation_prompt = ""
        if active:
            if self.remediation is None:
                return error(
                    ERR_SERVICE_UNAVAILABLE,
                    "Remediation prompt synthesizer not initialized.",
                )
            result = self.remediation.generate_remediation(active, rule_map)
            remediation_prompt = result.handoff_prompt

        if semantic_rubrics:
            header = "\n\n---\n### 🧠 Re-entrant Semantic Evaluation Required\n"
            footer = "\n**Note:** Semantic evaluation is mandatory. Please follow the rubrics above before completion.\n"
            combined_rubrics = header + "\n".join(semantic_rubrics) + footer
            remediation_prompt += combined_rubrics

        if self.telemetry is not None:
            self.telemetry.record_check(len(violations), len(active))

        if not active and not semantic_rubrics:
            return (
                "SUCCESS: Architecture compliant. Task may be marked complete."
                + coordination_info
            )

        return remediation_prompt + coordination_info

    async def fetch_rubric(
        self,
        target_file: str,
        rule_ids: list[str] | None = None,
    ) -> str:
        """
        Re-entrant Semantic Grading. Returns a rubric for the parent LLM to
        self-evaluate domain language and naming conventions.
        """
        rules = self._load_rules()
        semantic_rules = [r for r in rules if r.engine_type.value == "semantic"]
        if rule_ids:
            semantic_rules = [r for r in semantic_rules if r.id in rule_ids]

        scoped = ScopeFilter.filter_rules_for_file(target_file, semantic_rules, rules)
        if not scoped:
            return "NO_SEMANTIC_RULES: No semantic rules apply to this file."

        if self.semantic is None:
            return error(
                ERR_SERVICE_UNAVAILABLE,
                "Semantic analyzer not initialized.",
            )
        return self.semantic.build_rubric(target_file, scoped)

    async def init_governance(
        self,
        target_packs: list[str],
    ) -> str:
        """
        Agent-driven project bootstrap. Writes default rule packs
        from bundled resources to .aegis/rules/ and generates AGENTS.md.
        """
        installed = []
        if self.packs is None:
            return error(
                ERR_SERVICE_UNAVAILABLE,
                "Pack manager not initialized.",
            )
        for pack_name in target_packs:
            try:
                self.packs.install(pack_name)
                installed.append(pack_name)
            except ValueError as e:
                return error("SCAFFOLD_FAILED", str(e))

        self._deploy_all_workspace_instructions()
        await self.get_scorecard()

        packs_str = ", ".join(installed)
        return (
            f"SUCCESS: Governance framework scaffolded with packs: {packs_str}."
            " AGENTS.md, CLAUDE.md, and GEMINI.md generated in workspace root."
        )

    async def query_graph(
        self,
        query_type: str,
        target: str | None = None,
    ) -> str:
        """
        Introspect project structure.
        query_type: dependency_graph | module_health | hypothesis | rules
        """
        if query_type == "hypothesis":
            return self._hypothesize_workspace_architecture()

        if query_type == "dependency_graph":
            if not target:
                return error(
                    ERR_INVALID_INPUT,
                    "target module name required for dependency_graph",
                )
            if self.graph is None:
                return error(
                    ERR_SERVICE_UNAVAILABLE,
                    "Graph analyzer not initialized.",
                )
            result = self.graph.build_dependency_graph(self.workspace_root, target)
            return json.dumps(result, indent=2)

        if query_type == "module_health":
            if self.evaluation is None:
                return error(
                    ERR_SERVICE_UNAVAILABLE,
                    "Evaluation engine not initialized.",
                )
            rules = self._load_rules()
            violations = self.evaluation.evaluate_workspace(self.workspace_root, rules)
            by_module = {}
            for v in violations:
                module = v.file.split("/")[0] if "/" in v.file else "root"
                if module not in by_module:
                    by_module[module] = []
                by_module[module].append(v.rule_id)
            return json.dumps(
                {
                    m: {"count": len(ids), "rules": list(set(ids))}
                    for m, ids in by_module.items()
                },
                indent=2,
            )

        if query_type == "rules":
            rules = self._load_rules()
            return json.dumps(
                [
                    {
                        "id": r.id,
                        "description": r.description,
                        "severity": r.severity.value,
                        "category": r.category.value,
                    }
                    for r in rules
                ],
                indent=2,
            )

        return error(ERR_INVALID_INPUT, f"Unknown query_type: {query_type}")

    async def manage_rules(
        self,
        action: str,
        target: str | None = None,
        rule_id: str | None = None,
        description: str | None = None,
        severity: str = "HIGH",
        engine_type: str = "regex",
        category: str = "architecture",
        rationale: str | None = None,
        query: str | None = None,
        regex_pattern: str | None = None,
        applies_to: str | None = None,
        language: str = "python",
    ) -> str:
        """
        Agent-driven rule lifecycle management.
        action: suppress | remove_pack | add_rule
        """
        if action == "suppress":
            return await self._evolve_suppress(target)

        if action == "remove_pack":
            return await self._evolve_remove_pack(target)

        if action == "add_rule":
            return await self._evolve_add_rule(
                rule_id,
                description,
                severity,
                engine_type,
                category,
                rationale,
                query,
                regex_pattern,
                applies_to,
                language,
            )

        return error(ERR_INVALID_INPUT, f"Unknown action: {action}")

    async def _evolve_suppress(self, target: str | None) -> str:
        if not target:
            return error(ERR_INVALID_INPUT, "target rule_id required for suppress")
        rules = self._load_rules()
        rule = next((r for r in rules if r.id == target), None)
        if not rule:
            return error("RULE_NOT_FOUND", f"Rule '{target}' not found")
        if self.evaluation is None:
            return error(ERR_SERVICE_UNAVAILABLE, "Evaluation engine not initialized.")
        if self.baseline is None:
            return error(ERR_SERVICE_UNAVAILABLE, "Baseline manager not initialized.")
        violations = self.evaluation.evaluate_workspace(self.workspace_root, [rule])
        self.baseline.add_all_to_baseline(violations)
        return f"SUCCESS: Suppressed {len(violations)} violations for rule '{target}'"

    async def _evolve_remove_pack(self, target: str | None) -> str:
        if not target:
            return error(ERR_INVALID_INPUT, "target pack_name required")
        if self.packs is None:
            return error(ERR_SERVICE_UNAVAILABLE, "Pack manager not initialized.")
        try:
            self.packs.remove(target)
            return f"SUCCESS: Removed rule pack '{target}'"
        except ValueError as e:
            return error("REMOVE_FAILED", str(e))

    async def _evolve_add_rule(
        self,
        rule_id: str | None,
        description: str | None,
        severity: str,
        engine_type: str,
        category: str,
        rationale: str | None,
        query: str | None,
        regex_pattern: str | None,
        applies_to: str | None,
        language: str,
    ) -> str:
        from pathlib import Path

        import yaml

        if not rule_id or not description:
            return error(
                ERR_INVALID_INPUT,
                "rule_id and description are required for add_rule",
            )

        custom_path = Path(self.workspace_root) / ".aegis" / "rules" / "custom.yaml"
        custom_path.parent.mkdir(parents=True, exist_ok=True)

        new_rule: dict = {
            "id": rule_id,
            "description": description,
            "category": category,
            "engine_type": engine_type,
            "severity": severity,
            "mode": "block",
        }
        if rationale:
            new_rule["rationale"] = rationale
        if engine_type == "tree-sitter" and query:
            new_rule["query"] = query
        if engine_type == "regex" and regex_pattern:
            new_rule["query"] = regex_pattern
            new_rule["regex_pattern"] = regex_pattern
        if applies_to:
            new_rule["applies_to"] = [applies_to]
        if language:
            new_rule["language"] = language

        data: dict = {"rules": []}
        if custom_path.exists():
            existing = yaml.safe_load(custom_path.read_text())
            if existing and "rules" in existing:
                data["rules"] = existing["rules"]

        if any(r.get("id") == rule_id for r in data["rules"]):
            return error(
                "DUPLICATE_RULE",
                f"Rule ID '{rule_id}' already exists. Use a unique ID.",
            )

        data["rules"].append(new_rule)
        custom_path.write_text(yaml.dump(data, sort_keys=False))
        return f"SUCCESS: Rule '{rule_id}' appended to {custom_path}"

    async def plan_architecture(
        self,
        intent: str,
        file_path: str | None = None,
        code_string: str | None = None,
        language: str = "python",
    ) -> str:
        """
        Pre-emptive task alignment. Returns JIT-scoped rules
        that govern the file the agent is about to edit.
        If code_string is provided, validates the snippet in-memory
        and returns violations alongside scoped rules.
        """
        rules = self._load_rules()
        if file_path:
            relevant = ScopeFilter.filter_rules_for_file(file_path, rules, rules)
        else:
            relevant = rules[:15]

        lines = [f"## Architectural Context for: {intent}\n"]
        for r in relevant[:15]:
            lines.append(f"- **{r.id}** [{r.severity.value}] — {r.description}")

        if code_string and self.evaluation:
            try:
                violations = self.evaluation.evaluate_code_string(
                    code_string, language, relevant
                )
                if violations:
                    lines.append("\n### Code Violations Detected\n")
                    for v in violations[:10]:
                        lines.append(
                            f"- **{v.rule_id}** (line {v.line}): {v.description}"
                        )
                    rule_ids = {v.rule_id for v in violations}
                    lines.append(
                        f"\nFix these {len(rule_ids)} rule violations"
                        " before proceeding."
                    )
                else:
                    lines.append("\nNo violations detected in provided code snippet.")
            except Exception:
                pass

        return "\n".join(lines)

    async def find_patterns(self) -> DiscoveryResult:
        """
        Scans the workspace to detect frameworks and patterns.
        Returns a list of proposed governance laws for the team to review.
        """
        proposals = self._discover_proposals()

        return DiscoveryResult(
            proposals=proposals,
            message="Aegis has analyzed your project and proposes the following governance laws.",
        )

    async def apply_rules(
        self,
        law_id: str,
        custom_description: str | None = None,
    ) -> str:
        """
        Adopts a governance law for the project.
        law_id: Either a rule pack name (e.g., 'architecture') or a unique ID for a custom law.
        custom_description: If creating a custom law, provide its natural language definition.
        """
        # Case A: Rule Pack
        if self.packs and law_id in self.packs.list_available():
            return await self.init_governance(target_packs=[law_id])

        # Case B: Custom Law (Natural Language)
        if custom_description:
            # For simplicity, we use the existing manage_rules logic for 'add_rule'
            # But we wrap it into a "Semantic" rule by default for custom laws
            return await self.manage_rules(
                action="add_rule",
                rule_id=law_id,
                description=custom_description,
                engine_type="semantic",
                category="architecture",
            )

        return error(
            "INVALID_LAW",
            f"Law '{law_id}' not recognized. Provide custom_description for new laws.",
        )

    def _discover_proposals(self) -> list[Proposal]:
        root = Path(self.workspace_root)
        proposals: list[Proposal] = []

        pyproject = root / "pyproject.toml"
        package_json = root / "package.json"

        findings = []
        if pyproject.exists():
            findings.append("Python project (pyproject.toml)")
            deps = self._scan_pyproject_deps(pyproject)
            if deps:
                findings.append(f"Key dependencies: {', '.join(deps[:10])}")
        if package_json.exists():
            findings.append("Node.js/TypeScript project (package.json)")

        base_reason = " ".join(findings) if findings else "Generic project structure."

        # Determine architecture
        is_layered = False
        import_tiers = ""
        if self.graph is not None and pyproject.exists():
            try:
                g = self.graph.build_dependency_graph(self.workspace_root)
                tiers = g.get("tiers", {})
                if tiers:
                    import_tiers = ", ".join(tiers.keys())
                    is_layered = any(
                        t in ("api", "domain", "infra", "infrastructure", "core")
                        for t in tiers
                    )
            except Exception:
                pass

        # Security Proposal (Always)
        proposals.append(
            Proposal(
                id="security",
                relevance=1.0,
                reason=f"{base_reason} Security governance is mandatory for all projects.",
                suggested_action="apply_rules(law_id='security')",
            )
        )

        # Architecture Proposal
        arch_reason = base_reason
        if import_tiers:
            arch_reason += f" Import tiers detected: {import_tiers}."
        if is_layered:
            arch_reason += (
                " Layered (Domain-Driven) architecture detected via import boundaries."
            )
        else:
            arch_reason += " Monolithic or flat structure detected."

        proposals.append(
            Proposal(
                id="architecture",
                relevance=1.0,
                reason=arch_reason,
                suggested_action="apply_rules(law_id='architecture')",
            )
        )

        # Best Practices
        proposals.append(
            Proposal(
                id="best-practices",
                relevance=0.9,
                reason="Standardized best practices for code quality and maintainability.",
                suggested_action="apply_rules(law_id='best-practices')",
            )
        )

        # Style
        proposals.append(
            Proposal(
                id="style",
                relevance=0.8,
                reason="Enforce consistent naming and formatting conventions across the codebase.",
                suggested_action="apply_rules(law_id='style')",
            )
        )

        if not is_layered:
            proposals.append(
                Proposal(
                    id="structure",
                    relevance=0.7,
                    reason="Flat structure detected. Structure law helps organize modules as the project grows.",
                    suggested_action="apply_rules(law_id='structure')",
                )
            )

        return proposals

    def _hypothesize_workspace_architecture(self) -> str:
        proposals = self._discover_proposals()
        findings: list[str] = []
        for p in proposals:
            findings.append(f"Proposed: {p.id} (Relevance: {p.relevance}) - {p.reason}")

        return "\n".join(findings)

    def _scan_pyproject_deps(self, path: Path) -> list[str]:
        try:
            content = path.read_text()
            return re.findall(
                r'"([a-zA-Z][a-zA-Z0-9_-]+)"',
                content.split("[project]")[-1].split("[")[0],
            )
        except Exception:
            return []

    def _load_rules(self) -> list:
        if self.policy is None:
            return []
        try:
            rules = self.policy.parse_all(self.workspace_root)
            if hasattr(self, "plugin_registry") and self.plugin_registry:
                rules.extend(self.plugin_registry.auto_rules)
            return rules
        except Exception:
            return []

    def _get_cached_adjacency(self):
        from time import time

        now = time()
        if self._adjacency_cache_entry is not None:
            ts, adj = self._adjacency_cache_entry
            if now - ts < 5.0:
                return adj
        return None

    def _cache_adjacency(self, adjacency: dict):
        from time import time

        self._adjacency_cache_entry = (time(), adjacency)

    def _filter_rules_for_files(self, files_modified: list[str], rules: list) -> list:
        adjacency = self._get_cached_adjacency()
        if adjacency is None and self.graph is not None:
            try:
                adjacency, _ = self.graph.build_import_graph(self.workspace_root)
                if adjacency:
                    self._cache_adjacency(adjacency)
            except Exception:
                pass
        
        result: dict[str, object] = {}
        for file_path in files_modified:
            relevant = ScopeFilter.get_relevant_rules(
                file_path,
                rules,
                adjacency=adjacency,
                max_rules=100,
                base_dir=self.workspace_root,
            )
            for r in relevant:
                if r.id not in result:
                    result[r.id] = r
        return list(result.values())

    def _register_resources(self):
        @self.mcp.resource("aegis://rules")
        def get_rules() -> str:
            rules = self._load_rules()
            return json.dumps(
                [
                    {
                        "id": r.id,
                        "description": r.description,
                        "severity": r.severity.value,
                        "category": r.category.value,
                    }
                    for r in rules
                ],
                indent=2,
            )

        @self.mcp.resource("aegis://baseline")
        def get_baseline() -> str:
            if self.baseline is None:
                return json.dumps([])
            entries = self.baseline.load_baseline_raw()
            return json.dumps(entries, indent=2)

        @self.mcp.resource("aegis://context/{path}")
        def get_context(path: str) -> str:
            """
            Returns a Law Summary for the given path.
            Includes health score, top 3 critical rules, and link to scorecard.
            """
            rules = self._load_rules()
            scoped = ScopeFilter.filter_rules_for_file(path, rules, rules)

            # 1. Health Score for this file
            health_score = 100
            if self.evaluation and scoped:
                abs_path = os.path.join(self.workspace_root, path)
                if os.path.exists(abs_path):
                    file_violations = self.evaluation.evaluate_file(
                        abs_path, scoped, root_dir=self.workspace_root
                    )
                    active_violations = len(file_violations)
                    total_rules = len(scoped)
                    if total_rules > 0:
                        health_score = max(
                            0,
                            min(
                                100, int((1 - (active_violations / total_rules)) * 100)
                            ),
                        )

            # 2. Top 3 most critical rules
            from aegis.domain.policy.models import Severity

            severity_order = {
                Severity.CRITICAL: 0,
                Severity.HIGH: 1,
                Severity.MEDIUM: 2,
                Severity.LOW: 3,
                Severity.WARN: 4,
            }
            top_rules = sorted(
                scoped, key=lambda r: severity_order.get(r.severity, 99)
            )[:3]

            # 3. Formatted Law Summary
            summary = [f"### 🛡️ Aegis Law Summary for: `{path}`"]
            summary.append(f"**Module Health: {health_score}%**\n")

            if top_rules:
                summary.append("#### 📜 Top Critical Rules:")
                for r in top_rules:
                    summary.append(
                        f"- **{r.id}** [{r.severity.value}]: {r.description}"
                    )
            else:
                summary.append("No specific rules apply to this file.")

            summary.append(
                "\n[View full AEGIS.md scorecard](file:///"
                + str(Path(self.workspace_root) / ".aegis" / "AEGIS.md").replace("\\", "/")
                + ")"
            )

            return "\n".join(summary)

        @self.mcp.resource("aegis://scorecard")
        def _read_scorecard() -> str:
            """
            Returns the full content of AEGIS.md.
            """
            scorecard_path = Path(self.workspace_root) / ".aegis" / "AEGIS.md"
            if scorecard_path.exists():
                return scorecard_path.read_text()

            return (
                "# 🛡️ Aegis Project Health Scorecard\n\n"
                "AEGIS.md not found. Run `aegis init_governance` to generate it."
            )

        @self.mcp.resource("aegis://spec")
        def get_spec() -> str:
            spec_path = Path(self.workspace_root) / "docs" / "SPEC.md"
            if spec_path.exists():
                return spec_path.read_text()
            return warn(
                "No docs/SPEC.md found in workspace. "
                "The human developer has not defined an architectural specification."
            )

    def _register_prompts(self):
        @self.mcp.prompt()
        def evaluate_architecture(files: list[str]) -> str:
            return (
                f"Call check_architecture with "
                f"files_modified={files} before declaring the task complete."
            )

        @self.mcp.prompt()
        def remediate_violations() -> str:
            return (
                "1. Read the violation report from check_architecture.\n"
                "2. For each violation, read the affected file at the specified line.\n"
                "3. Apply the remediation while preserving business logic.\n"
                "4. Re-run check_architecture to verify."
            )

        @self.mcp.prompt()
        def initialize_governance() -> str:
            return (
                "1. Call query_graph(query_type='hypothesis') "
                "to discover the workspace architecture.\n"
                "2. Present the proposed architecture to the user for approval.\n"
                "3. Call init_governance with the approved pack list."
            )

        @self.mcp.prompt()
        def inspect_dependency(module: str) -> str:
            return (
                f"Call query_graph(query_type='dependency_graph', "
                f"target='{module}') to inspect dependencies."
            )

    def _deploy_all_workspace_instructions(self):
        from aegis.infrastructure.installer import AgentNativeInstaller

        installer = AgentNativeInstaller()
        installer.init_workspace(workspace_root=self.workspace_root, instructions_only=True)

    def run_headless_check(self) -> int:
        """Run a single compliance check and return violation count."""
        rules = self._load_rules()
        if not rules:
            print("WARN: No rules loaded. Run /aegis-init first.")
            return 0

        if self.evaluation is None:
            print("ERROR: Evaluation engine not initialized.")
            return -1

        violations = self.evaluation.evaluate_workspace(self.workspace_root, rules)
        active = [
            v
            for v in violations
            if not (
                self.baseline
                and self.baseline.is_exempt(
                    v, next((r for r in rules if r.id == v.rule_id), None)
                )
            )
        ]

        if self.telemetry:
            self.telemetry.record_check(len(violations), len(active))

        if active:
            print(f"Violations found: {len(active)}")
            for v in active[:20]:
                print(f"  {v.file}:{v.line}  [{v.rule_id}] {v.description}")
            return len(active)

        print("SUCCESS: Architecture compliant.")
        return 0

    def run(self, transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000):
        if transport == "stdio":
            self.mcp.run(transport="stdio")
        elif transport in ("sse", "streamable-http"):
            import uvicorn

            if transport == "sse":
                app = self.mcp.sse_app()
            else:
                app = self.mcp.streamable_http_app()
            uvicorn.run(app, host=host, port=port)
        else:
            raise ValueError(f"Unknown transport: {transport}")

    def _get_agent_id(self) -> str:
        """Detect agent ID from environment variables."""
        return (
            os.getenv("CLAUDE_AGENT_ID")
            or os.getenv("AIDER_AGENT_ID")
            or os.getenv("AEGIS_AGENT_ID")
            or "unknown"
        )
