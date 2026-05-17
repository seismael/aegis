import asyncio
import os
import structlog
from typing import Optional, List
from mcp.server.fastmcp import FastMCP
from aegis.core.container.app import Container
from aegis.domain.enforcement.remediation import RemediationPromptSynthesizer
from aegis.infrastructure.graph_analyzer import GraphAnalyzer


class AegisKernel:
    """
    The headless execution heart of Aegis.
    Acts as an MCP server providing architectural diagnostics to AI agents.
    """

    def __init__(self):
        self.logger = structlog.get_logger()
        self.mcp = FastMCP("Aegis Architecture Engine")
        self.container = Container()
        self.remediation_synthesizer = RemediationPromptSynthesizer()
        self._register_tools()
        self._register_plugin_tools()

    def _register_tools(self):
        self.mcp.tool()(self.get_architecture_spec)
        self.mcp.tool()(self.validate_architecture_compliance)
        self.mcp.tool()(self.apply_architectural_remediation)
        self.mcp.tool()(self.get_rule_rationale)
        self.mcp.tool()(self.get_dependency_graph)

    def _register_plugin_tools(self):
        for tool_fn in self.container.custom_mcp_tools:
            wrapped = self.mcp.tool()(tool_fn)
            self.logger.info(
                "Registered custom MCP tool", tool=tool_fn.__name__
            )

    async def get_architecture_spec(self) -> str:
        """Retrieves the current project architectural specification (SPEC.md)."""
        try:
            spec_path = os.path.join(
                self.container.workspace_root, "SPEC.md"
            )
            if not os.path.exists(spec_path):
                return "No SPEC.md found. Architecture is currently undefined."
            with open(spec_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading specification: {str(e)}"

    async def validate_architecture_compliance(
        self, staged_only: bool = True
    ) -> str:
        """
        Validates code against the architectural matrix.
        Returns a scorecard of NEW violations for the agent to resolve.
        """
        rules_path = os.path.join(
            self.container.workspace_root, ".aegis", "rules.yaml"
        )
        if not os.path.exists(rules_path):
            return "Aegis is not initialized. Run `/aegis-init` to establish governance."

        rules = self.container.policy_parser.parse_rules(rules_path)

        if staged_only:
            violations = self.container.evaluation_service.evaluate_changes(rules)
        else:
            violations = self.container.evaluation_service.evaluate_workspace(
                self.container.workspace_root, rules
            )

        active = [
            v
            for v in violations
            if not self.container.baseline_manager.is_exempt(v)
        ]

        if not active:
            return "✅ Architecture compliance check passed. No NEW violations detected."

        report = "⚠️ ARCHITECTURAL DRIFT DETECTED\n"
        report += (
            "The following NEW violations must be resolved before proceeding:\n\n"
        )
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
        rules_path = os.path.join(
            self.container.workspace_root, ".aegis", "rules.yaml"
        )
        rules = self.container.policy_parser.parse_rules(rules_path)
        rules_map = {r.id: r for r in rules}

        violations = self.container.evaluation_service.evaluate_workspace(
            self.container.workspace_root, rules
        )
        active = [
            v
            for v in violations
            if not self.container.baseline_manager.is_exempt(v)
        ]

        if not active:
            return "✅ Architecture is compliant. No remediation needed."

        return self.remediation_synthesizer.generate_remediation(
            active, rules_map
        )

    async def get_rule_rationale(self, rule_id: str) -> str:
        """
        Fetches the human consensus history for a given rule.
        Returns the rationale and evolution decisions from evolution_log.json.
        """
        rules_path = os.path.join(
            self.container.workspace_root, ".aegis", "rules.yaml"
        )
        all_rules = self.container.policy_parser.parse_rules(rules_path)
        rule = next((r for r in all_rules if r.id == rule_id), None)

        if not rule:
            return f"Rule '{rule_id}' not found in the governance matrix."

        result = f"## Rule: {rule.id}\n"
        result += f"**Description:** {rule.description}\n"
        result += f"**Engine:** {rule.engine_type.value}\n"
        result += f"**Mode:** {rule.mode.value}\n"
        result += f"**Severity:** {rule.severity.value}\n"
        if rule.rationale:
            result += f"**Rationale:** {rule.rationale}\n"

        log = self.container.evolution_service.load_log()
        decisions = [d for d in log.decisions if d.rule_id == rule_id]

        if decisions:
            result += "\n### Evolution History\n"
            for d in decisions:
                result += (
                    f"- **{d.timestamp}** — {d.action}: {d.rationale}\n"
                )
        else:
            result += "\nNo evolution history recorded for this rule."

        return result

    async def get_dependency_graph(self, node_name: str) -> str:
        """
        Returns the import dependencies for a given module name.
        Shows what the module imports and what imports it.
        """
        from aegis.core.models.governance import EngineType, Rule

        # Build the full dependency graph
        analyzer = GraphAnalyzer()
        adjacency, _ = analyzer._build_import_graph(
            self.container.workspace_root
        )

        if not adjacency:
            return (
                "No Python modules found in the workspace "
                "or unable to parse dependency graph."
            )

        # Find the requested node (fuzzy match: any node containing the name)
        matched = [m for m in adjacency if node_name in m]

        if not matched:
            return (
                f"Module '{node_name}' not found in the dependency graph. "
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
            importers = [
                m for m, deps in adjacency.items() if module in deps
            ]
            if importers:
                result += "**Imported by:**\n"
                for imp in sorted(importers):
                    result += f"- `{imp}`\n"

            result += "\n"

        return result

    def run(self):
        self.mcp.run()

    @staticmethod
    def entry_point():
        kernel = AegisKernel()
        kernel.run()


if __name__ == "__main__":
    AegisKernel.entry_point()
