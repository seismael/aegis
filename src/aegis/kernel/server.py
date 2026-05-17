import logging
import os
import re

import structlog
from mcp.server.fastmcp import FastMCP

from aegis.core.container.app import Container
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

    def _register_tools(self):
        self.mcp.tool()(self.get_architecture_spec)
        self.mcp.tool()(self.validate_architecture_compliance)
        self.mcp.tool()(self.apply_architectural_remediation)
        self.mcp.tool()(self.get_rule_rationale)
        self.mcp.tool()(self.get_dependency_graph)
        self.mcp.tool()(self.server_status)

    def _register_prompts(self):
        """Register reusable MCP prompts for agentic workflows."""

        @self.mcp.prompt(
            name="evaluate-architecture",
            description="Run a full architecture compliance evaluation on the workspace",
        )
        def evaluate_architecture_prompt() -> str:
            return (
                "You are an architectural governance agent. "
                "Run `validate_architecture_compliance` on the full workspace. "
                "If violations are found, call `apply_architectural_remediation` "
                "for structured fix instructions, then resolve each violation "
                "one by one. Re-validate after each fix."
            )

        @self.mcp.prompt(
            name="remediate-violations",
            description="Fix all active architectural violations step by step",
        )
        def remediate_violations_prompt() -> str:
            return (
                "You are a remediation agent. Call `apply_architectural_remediation` "
                "to get the current violation list with fix instructions. For each "
                "violation: (1) read the affected file, (2) apply the suggested fix, "
                "(3) re-run `validate_architecture_compliance` to confirm the fix "
                "resolved it. Repeat until all violations are cleared."
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
            "aegis://rules", description="Architectural governance rules (rules.yaml)"
        )
        async def get_rules_resource() -> str:
            path = os.path.join(self._workspace_root, ".aegis", "rules.yaml")
            if not os.path.exists(path):
                return "ERROR: rules.yaml not found."
            try:
                with open(path, encoding="utf-8") as f:
                    return f.read()
            except OSError as e:
                self.logger.error("Failed to read rules resource", path=path, error=str(e))
                return f"ERROR: reading rules.yaml — {e}"

        @self.mcp.resource(
            "aegis://baseline", description="Architectural debt ledger (baseline.json)"
        )
        async def get_baseline_resource() -> str:
            path = os.path.join(
                self._workspace_root, ".aegis", "baseline.json"
            )
            if not os.path.exists(path):
                return "WARN: baseline.json not found — no debt ledger established."
            try:
                with open(path, encoding="utf-8") as f:
                    return f.read()
            except OSError as e:
                self.logger.error("Failed to read baseline resource", path=path, error=str(e))
                return f"ERROR: reading baseline.json — {e}"

        @self.mcp.resource(
            "aegis://evolution",
            description="Rule evolution history (evolution_log.json)",
        )
        async def get_evolution_resource() -> str:
            path = os.path.join(
                self._workspace_root, ".aegis", "evolution_log.json"
            )
            if not os.path.exists(path):
                return "WARN: evolution_log.json not found — no evolution history recorded."
            try:
                with open(path, encoding="utf-8") as f:
                    return f.read()
            except OSError as e:
                self.logger.error("Failed to read evolution resource", path=path, error=str(e))
                return f"ERROR: reading evolution_log.json — {e}"

        @self.mcp.resource(
            "aegis://spec", description="Architecture specification (SPEC.md)"
        )
        async def get_spec_resource() -> str:
            path = os.path.join(self._workspace_root, "SPEC.md")
            if not os.path.exists(path):
                return "WARN: SPEC.md not found — architecture is undefined."
            try:
                with open(path, encoding="utf-8") as f:
                    return f.read()
            except OSError as e:
                self.logger.error("Failed to read spec resource", path=path, error=str(e))
                return f"ERROR: reading SPEC.md — {e}"

    def _register_plugin_tools(self):
        if self.container is None:
            self.logger.warning("Container unavailable — skipping plugin tool registration")
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
        """Retrieves the current project architectural specification (SPEC.md)."""
        try:
            spec_path = os.path.join(self._workspace_root, "SPEC.md")
            if not os.path.exists(spec_path):
                return "WARN: SPEC.md not found. Architecture is currently undefined."
            with open(spec_path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.logger.error("Failed to read spec", error=str(e))
            return f"ERROR: reading specification — {str(e)}"

    async def server_status(self) -> str:
        """
        Returns server health and capability overview.
        Lists registered tools, resources, and prompts with counts.
        """
        try:
            root = self._workspace_root
            rules_path = os.path.join(root, ".aegis", "rules.yaml")

            rules = []
            active = []
            plugin_count = 0
            plugin_tools = 0

            if self._policy_parser and os.path.exists(rules_path):
                rules = self._policy_parser.parse_rules(rules_path)
            if self._evaluation_service and self._baseline_manager:
                violations = self._evaluation_service.evaluate_workspace(root, rules)
                active = [v for v in violations if not self._baseline_manager.is_exempt(v)]
            if self.container is not None:
                plugin_tools = len(self.container.custom_mcp_tools)
                plugin_count = len(self.container.loaded_plugins)

            container_status = "degraded" if self.container is None else "ready"
            summary = "## Aegis Kernel Status\n\n"
            summary += f"- **Version:** {_VERSION}\n"
            summary += f"- **Status:** {container_status}\n"
            summary += f"- **Workspace:** `{root}`\n"
            summary += f"- **Rules:** {len(rules)} loaded\n"
            summary += f"- **Tools:** 6 built-in + {plugin_tools} plugin\n"
            summary += "- **Resources:** 4 governance artifacts\n"
            summary += "- **Prompts:** 4 workflow templates\n"
            summary += f"- **Violations:** {len(active)} active\n"
            summary += f"- **Plugins:** {plugin_count} loaded\n"
            return summary
        except Exception as e:
            self.logger.error("Status check failed", error=str(e))
            return f"ERROR: status check failed — {str(e)}"

    async def validate_architecture_compliance(self, staged_only: bool = True) -> str:
        """
        Validates code against the architectural matrix.
        Returns a scorecard of NEW violations for the agent to resolve.
        """
        if self.container is None:
            return "ERROR: Kernel not fully initialized — container unavailable."

        root = self._workspace_root
        rules_path = os.path.join(root, ".aegis", "rules.yaml")
        if not os.path.exists(rules_path):
            return "ERROR: Aegis is not initialized — run `/aegis-init` to establish governance."

        rules = self._policy_parser.parse_rules(rules_path)

        if staged_only:
            violations = self._evaluation_service.evaluate_changes(rules)
        else:
            violations = self._evaluation_service.evaluate_workspace(root, rules)

        active = [v for v in violations if not self._baseline_manager.is_exempt(v)]

        if not active:
            return "PASS: Architecture compliance check passed. No new violations detected."

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
        MCP Tool: Called when a compliance check fails.
        Returns a highly structured prompt instructing the AI how to fix the code.
        """
        if self.container is None:
            return "ERROR: Kernel not fully initialized — container unavailable."

        root = self._workspace_root
        rules_path = os.path.join(root, ".aegis", "rules.yaml")
        rules = self._policy_parser.parse_rules(rules_path)
        rules_map = {r.id: r for r in rules}

        violations = self._evaluation_service.evaluate_workspace(root, rules)
        active = [v for v in violations if not self._baseline_manager.is_exempt(v)]

        if not active:
            return "PASS: Architecture is compliant. No remediation needed."

        if self.remediation_synthesizer is None:
            return "ERROR: Remediation synthesizer unavailable."

        return self.remediation_synthesizer.generate_remediation(active, rules_map)

    async def get_rule_rationale(self, rule_id: str) -> str:
        """
        Fetches the human consensus history for a given rule.
        Returns the rationale and evolution decisions from evolution_log.json.
        """
        if not rule_id or not rule_id.strip():
            return "ERROR: rule_id must be a non-empty string."

        if not re.match(r"^[a-zA-Z0-9_-]+$", rule_id):
            return f"ERROR: rule_id '{rule_id}' contains invalid characters."

        if self._policy_parser is None:
            return "ERROR: Policy parser unavailable — container not initialized."

        root = self._workspace_root
        rules_path = os.path.join(root, ".aegis", "rules.yaml")
        all_rules = self._policy_parser.parse_rules(rules_path)
        rule = next((r for r in all_rules if r.id == rule_id), None)

        if not rule:
            return f"WARN: rule '{rule_id}' not found in the governance matrix."

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
        Returns the import dependencies for a given module name.
        Shows what the module imports and what imports it.
        """
        if not node_name or not node_name.strip():
            return "ERROR: node_name must be a non-empty string."

        # Prevent path traversal in module name
        if ".." in node_name or node_name.startswith("/") or node_name.startswith("\\"):
            return f"ERROR: node_name '{node_name}' is not a valid module name."

        # Build the full dependency graph
        analyzer = GraphAnalyzer()
        adjacency, _ = analyzer.build_import_graph(self._workspace_root)

        if not adjacency:
            return (
                "WARN: no Python modules found in the workspace "
                "or unable to parse dependency graph."
            )

        # Find the requested node (fuzzy match: any node containing the name)
        matched = [m for m in adjacency if node_name in m]

        if not matched:
            return (
                f"WARN: module '{node_name}' not found in the dependency graph.\n"
                f"Available roots: {', '.join(sorted(adjacency.keys())[:10])}"
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

    def run(self, transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000):
        """
        Runs the MCP server with the given transport.

        Args:
            transport: One of "stdio", "sse", or "streamable-http".
            host: Host to bind (SSE/HTTP only).
            port: Port to bind (SSE/HTTP only).
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
            uvicorn.run(app, host=host, port=port, log_level="warning")
        else:
            raise ValueError(f"Unsupported transport: {transport}")

    @staticmethod
    def entry_point():
        import argparse

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
