import json
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
            self.packs = RulePackManager(self._workspace_root)
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
        from bundled resources to .aegis/rules/.
        """
        installed = []
        for pack_name in target_packs:
            try:
                self.packs.install(pack_name)
                installed.append(pack_name)
            except ValueError as e:
                return error("SCAFFOLD_FAILED", str(e))

        packs_str = ", ".join(installed)
        return f"SUCCESS: Governance framework scaffolded with packs: {packs_str}"

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
    ) -> str:
        """
        Agent-driven rule lifecycle management.
        action: suppress | install_pack | remove_pack
        """
        if action == "suppress":
            if not target:
                return error(ERR_INVALID_INPUT, "target rule_id required for suppress")
            rules = self._load_rules()
            rule = next((r for r in rules if r.id == target), None)
            if not rule:
                return error("RULE_NOT_FOUND", f"Rule '{target}' not found")
            violations = self.evaluation.evaluate_workspace(self.workspace_root, [rule])
            self.baseline.add_all_to_baseline(violations)
            return (
                f"SUCCESS: Suppressed {len(violations)} violations for rule '{target}'"
            )

        if action == "install_pack":
            if not target:
                return error(ERR_INVALID_INPUT, "target pack_name required")
            try:
                self.packs.install(target)
                return f"SUCCESS: Installed rule pack '{target}'"
            except ValueError as e:
                return error("INSTALL_FAILED", str(e))

        if action == "remove_pack":
            if not target:
                return error(ERR_INVALID_INPUT, "target pack_name required")
            try:
                self.packs.remove(target)
                return f"SUCCESS: Removed rule pack '{target}'"
            except ValueError as e:
                return error("REMOVE_FAILED", str(e))

        return error(ERR_INVALID_INPUT, f"Unknown action: {action}")

    async def plan_architecture(
        self,
        intent: str,
        file_path: str | None = None,
    ) -> str:
        """
        Pre-emptive task alignment. Returns JIT-scoped rules
        that govern the file the agent is about to edit.
        """
        rules = self._load_rules()
        if file_path:
            relevant = ScopeFilter.filter_rules_for_file(file_path, rules, rules)
        else:
            relevant = rules[:15]

        lines = [f"## Architectural Context for: {intent}\n"]
        for r in relevant[:15]:
            lines.append(f"- **{r.id}** [{r.severity.value}] — {r.description}")
        return "\n".join(lines)

    def _hypothesize_workspace_architecture(self) -> str:
        root = Path(self.workspace_root)
        pyproject = root / "pyproject.toml"
        package_json = root / "package.json"

        findings = []

        if pyproject.exists():
            findings.append("Detected: Python project (pyproject.toml)")
            deps = self._scan_pyproject_deps(pyproject)
            if deps:
                findings.append(f"Key dependencies: {', '.join(deps[:10])}")
        if package_json.exists():
            findings.append("Detected: Node.js/TypeScript project (package.json)")

        src_dir = root / "src"
        if src_dir.exists():
            packages = [
                d.name
                for d in src_dir.iterdir()
                if d.is_dir() and not d.name.startswith("_")
            ]
            if packages:
                findings.append(f"Source packages: {', '.join(packages[:10])}")

        findings.append(
            "\nProposed architecture: Layered (Domain-Driven) with hexagonal isolation."
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
            return "No SPEC.md found."

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
