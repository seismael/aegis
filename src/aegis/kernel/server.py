import json
import os
import re
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
from aegis.domain.evaluation.service import EvaluationService
from aegis.domain.observability.telemetry import TelemetryRecorder
from aegis.domain.policy.pack_manager import RulePackManager
from aegis.domain.policy.parser import PolicyParser
from aegis.kernel.errors import (
    ERR_INVALID_INPUT,
    error,
    warn,
)

_VERSION = "0.4.0"


class AegisKernel:
    """
    V4 Agent-Native Microkernel.
    Headless MCP server providing 6 tools for architectural governance.
    Every dependency is constructor-injected — no DI container.
    """

    def __init__(
        self,
        workspace_root: str | None = None,
    ):
        self.logger = structlog.get_logger()
        self._workspace_root = workspace_root or self._discover_root()

        try:
            self.policy = PolicyParser(self._workspace_root)
        except Exception:
            self.policy = None
        try:
            self.regex = RegexAnalyzer()
            self.tree_sitter = TreeSitterAnalyzer()
            self.graph = GraphAnalyzer()
            self.semantic = SemanticAnalyzer()
            self.evaluation = EvaluationService(
                tree_sitter_analyzer=self.tree_sitter,
                graph_analyzer=self.graph,
                regex_analyzer=self.regex,
                semantic_analyzer=self.semantic,
            )
        except Exception:
            self.regex = self.tree_sitter = None
            self.graph = self.semantic = None
            self.evaluation = None
        try:
            self.baseline = BaselineManager(self._workspace_root)
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
            self.remediation = RemediationPromptSynthesizer()
        except Exception:
            self.remediation = None

        self.mcp = FastMCP("Aegis Architecture Engine")
        self._register_tools()
        self._register_resources()
        self._register_prompts()

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
        self.mcp.tool()(self.validate_architecture_compliance)
        self.mcp.tool()(self.request_semantic_grading_rubric)
        self.mcp.tool()(self.scaffold_governance_framework)
        self.mcp.tool()(self.query_knowledge_graph)
        self.mcp.tool()(self.evolve_ruleset)
        self.mcp.tool()(self.plan_architecture)

    async def validate_architecture_compliance(
        self,
        files_modified: list[str],
        phase: str = "pre-commit",
    ) -> str:
        """
        JIT Compliance Gate. Call before declaring any task complete.
        Returns SUCCESS string or formatted violation report with remediation.
        """
        rules = self._load_rules()
        if not rules:
            return warn("No rules loaded. Run /aegis-init first.")

        phase_enum = None
        try:
            from aegis.domain.policy.models import EvaluationPhase

            phase_enum = EvaluationPhase(phase)
        except ValueError:
            pass

        filtered = self._filter_rules_for_files(files_modified, rules)

        rule_map = {r.id: r for r in rules}
        violations = self.evaluation.evaluate_workspace(
            self.workspace_root, filtered, phase=phase_enum
        )

        active = [
            v
            for v in violations
            if not self.baseline.is_exempt(v, rule_map.get(v.rule_id))
        ]

        if not active:
            self.telemetry.record_check(len(violations), 0)
            return "SUCCESS: Architecture compliant. Task may be marked complete."

        self.telemetry.record_check(len(violations), len(active))
        result = self.remediation.generate_remediation(active, rule_map)
        return result.handoff_prompt

    async def request_semantic_grading_rubric(
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

        return self.semantic.build_rubric(target_file, scoped)

    async def scaffold_governance_framework(
        self,
        target_packs: list[str],
    ) -> str:
        """
        Agent-driven project bootstrap. Writes default rule packs
        from bundled resources to .aegis/rules/ and generates AGENTS.md.
        """
        installed = []
        for pack_name in target_packs:
            try:
                self.packs.install(pack_name)
                installed.append(pack_name)
            except ValueError as e:
                return error("SCAFFOLD_FAILED", str(e))

        self._generate_agents_md()

        packs_str = ", ".join(installed)
        return (
            f"SUCCESS: Governance framework scaffolded with packs: {packs_str}."
            " AGENTS.md generated in workspace root."
        )

    async def query_knowledge_graph(
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
            result = self.graph.build_dependency_graph(self.workspace_root, target)
            return json.dumps(result, indent=2)

        if query_type == "module_health":
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

    async def evolve_ruleset(
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
        violations = self.evaluation.evaluate_workspace(self.workspace_root, [rule])
        self.baseline.add_all_to_baseline(violations)
        return f"SUCCESS: Suppressed {len(violations)} violations for rule '{target}'"

    async def _evolve_remove_pack(self, target: str | None) -> str:
        if not target:
            return error(ERR_INVALID_INPUT, "target pack_name required")
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

    def _hypothesize_workspace_architecture(self) -> str:
        root = Path(self.workspace_root)
        findings: list[str] = []

        pyproject = root / "pyproject.toml"
        package_json = root / "package.json"

        if pyproject.exists():
            findings.append("Detected: Python project (pyproject.toml)")
            deps = self._scan_pyproject_deps(pyproject)
            if deps:
                findings.append(f"Key dependencies: {', '.join(deps[:10])}")
        if package_json.exists():
            findings.append("Detected: Node.js/TypeScript project (package.json)")

        if self.graph is not None and pyproject.exists():
            try:
                g = self.graph.build_dependency_graph(self.workspace_root)
                tiers = g.get("tiers", {})
                if tiers:
                    tier_names = ", ".join(tiers.keys())
                    findings.append(f"\nImport tiers detected: {tier_names}")
                    findings.append(f"Module count: {g['total_modules']}")

                    layered = any(
                        t in ("api", "domain", "infra", "infrastructure", "core")
                        for t in tiers
                    )
                    if layered:
                        findings.append(
                            "Architecture: Layered (Domain-Driven) detected"
                            " via import boundaries."
                        )
                        findings.append(
                            "Recommended packs: architecture, security, "
                            "best-practices, style"
                        )
                    else:
                        findings.append(
                            "Architecture: Monolithic or flat structure detected."
                        )
                        findings.append(
                            "Recommended packs: architecture, best-practices, "
                            "structure, style"
                        )
                else:
                    findings.append(
                        "\nProposed architecture: Layered (Domain-Driven) "
                        "with hexagonal isolation."
                    )
                    findings.append(
                        "Recommended packs: architecture, security, "
                        "best-practices, style"
                    )
            except Exception:
                findings.append(
                    "\nProposed architecture: Layered (Domain-Driven) "
                    "with hexagonal isolation."
                )
                findings.append(
                    "Recommended packs: architecture, security, best-practices, style"
                )
        else:
            findings.append(
                "\nProposed architecture: Layered (Domain-Driven) "
                "with hexagonal isolation."
            )
            findings.append(
                "Recommended packs: architecture, security, best-practices, style"
            )

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
        try:
            return self.policy.parse_all(self.workspace_root)
        except Exception:
            return []

    def _filter_rules_for_files(self, files_modified: list[str], rules: list) -> list:
        return ScopeFilter.filter_rules_for_files(files_modified, rules)

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
            entries = self.baseline.load_baseline_raw()
            return json.dumps(entries, indent=2)

        @self.mcp.resource("aegis://context/{path}")
        def get_context(path: str) -> str:
            rules = self._load_rules()
            scoped = ScopeFilter.filter_rules_for_file(path, rules, rules)
            return json.dumps(
                [
                    {
                        "id": r.id,
                        "description": r.description,
                        "severity": r.severity.value,
                    }
                    for r in scoped[:15]
                ],
                indent=2,
            )

        @self.mcp.resource("aegis://spec")
        def get_spec() -> str:
            spec_path = Path(self.workspace_root) / "SPEC.md"
            if spec_path.exists():
                return spec_path.read_text()
            return warn(
                "No SPEC.md found in workspace. "
                "Create one via /aegis-init or scaffold_governance_framework."
            )

    def _register_prompts(self):
        @self.mcp.prompt()
        def evaluate_architecture(files: list[str]) -> str:
            return (
                f"Call validate_architecture_compliance with "
                f"files_modified={files} before declaring the task complete."
            )

        @self.mcp.prompt()
        def remediate_violations() -> str:
            return (
                "1. Read the violation report from validate_architecture_compliance.\n"
                "2. For each violation, read the affected file at the specified line.\n"
                "3. Apply the remediation while preserving business logic.\n"
                "4. Re-run validate_architecture_compliance to verify."
            )

        @self.mcp.prompt()
        def initialize_governance() -> str:
            return (
                "1. Call query_knowledge_graph(query_type='hypothesis') "
                "to discover the workspace architecture.\n"
                "2. Present the proposed architecture to the user for approval.\n"
                "3. Call scaffold_governance_framework with the approved pack list."
            )

        @self.mcp.prompt()
        def inspect_dependency(module: str) -> str:
            return (
                f"Call query_knowledge_graph(query_type='dependency_graph', "
                f"target='{module}') to inspect dependencies."
            )

    def _generate_agents_md(self):
        from aegis.infrastructure.installer import AgentNativeInstaller

        AgentNativeInstaller.generate_agents_template(self.workspace_root)

    def run_headless_check(self) -> int:
        """Run a single compliance check and return violation count."""
        rules = self._load_rules()
        if not rules:
            print("WARN: No rules loaded. Run /aegis-init first.")
            return 0

        violations = self.evaluation.evaluate_workspace(self.workspace_root, rules)
        active = [
            v
            for v in violations
            if not self.baseline.is_exempt(
                v, next((r for r in rules if r.id == v.rule_id), None)
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
