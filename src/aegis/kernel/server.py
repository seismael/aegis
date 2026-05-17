import asyncio
import os
import structlog
from typing import Optional, List
from mcp.server.fastmcp import FastMCP
from aegis.core.container.app import Container

class AegisKernel:
    """
    The headless execution heart of Aegis.
    Acts as an MCP server providing architectural diagnostics to AI agents.
    """
    def __init__(self):
        self.logger = structlog.get_logger()
        self.mcp = FastMCP("Aegis Architecture Engine")
        self.container = Container()
        self._register_tools()

    def _register_tools(self):
        self.mcp.tool()(self.get_architecture_spec)
        self.mcp.tool()(self.validate_architecture_compliance)
        self.mcp.tool()(self.get_remediation_prompt)

    async def get_architecture_spec(self) -> str:
        """Retrieves the current project architectural specification (SPEC.md)."""
        try:
            spec_path = os.path.join(self.container.workspace_root, "SPEC.md")
            if not os.path.exists(spec_path):
                return "No SPEC.md found. Architecture is currently undefined."
            with open(spec_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading specification: {str(e)}"

    async def validate_architecture_compliance(self, staged_only: bool = True) -> str:
        """
        Validates code against the architectural matrix.
        Returns a scorecard of NEW violations for the agent to resolve.
        """
        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        if not os.path.exists(rules_path):
            return "Aegis is not initialized. Run `/aegis-init` to establish governance."

        rules = self.container.policy_parser.parse_rules(rules_path)
        
        if staged_only:
            violations = self.container.evaluation_service.evaluate_changes(rules)
        else:
            violations = self.container.evaluation_service.evaluate_workspace(self.container.workspace_root, rules)
            
        active = [v for v in violations if not self.container.baseline_manager.is_exempt(v)]
        
        if not active:
            return "✅ Architecture compliance check passed. No NEW violations detected."
        
        report = "⚠️ ARCHITECTURAL DRIFT DETECTED\n"
        report += "The following NEW violations must be resolved before proceeding:\n\n"
        for v in active:
            report += f"- [{v.severity}] {v.file}:{v.line}\n"
            report += f"  Violation: {v.description} ({v.rule_id})\n"
            
        report += "\nUse the `get_remediation_prompt` tool to receive specific refactoring instructions."
        return report

    async def get_remediation_prompt(self, violation_rule_id: str) -> str:
        """
        Provides a strictly formatted prompt describing how to fix a specific violation.
        The AI agent should use its own reasoning to apply the fix based on this prompt.
        """
        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        all_rules = self.container.policy_parser.parse_rules(rules_path)
        rule = next((r for r in all_rules if r.id == violation_rule_id), None)
        
        if not rule:
            return f"Rule '{violation_rule_id}' not found in the governance matrix."

        prompt = f"### ARCHITECTURAL REFACTORING INSTRUCTION: {rule.id}\n\n"
        prompt += f"**Constraint**: {rule.description}\n"
        prompt += f"**Logical Pattern (S-Expression)**: `{rule.query or rule.candidates_query}`\n\n"
        prompt += "**Refactoring Strategy**:\n"
        prompt += "1. Analyze the violating nodes identified by the engine.\n"
        prompt += "2. Restructure the code to comply with the constraint while preserving business logic.\n"
        prompt += "3. Ensure all related tests pass after the refactor.\n"
        prompt += "4. If the rule is too restrictive, use `/aegis-evolve` to negotiate a change."
        
        return prompt

    def run(self):
        self.mcp.run()

    @staticmethod
    def entry_point():
        kernel = AegisKernel()
        kernel.run()

if __name__ == "__main__":
    AegisKernel.entry_point()
