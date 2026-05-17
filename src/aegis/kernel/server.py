import asyncio
import os
import structlog
from typing import Optional
from mcp.server.fastmcp import FastMCP
from aegis.core.container.app import Container
from aegis.core.models.remediation import RemediationAction, RemediationPlan

class AegisKernel:
    """
    Encapsulates the MCP server logic to comply with Strict OOD.
    """
    def __init__(self):
        self.logger = structlog.get_logger()
        self.mcp = FastMCP("Aegis Architecture Engine")
        self.container = Container()
        self._register_tools()

    def _register_tools(self):
        self.mcp.tool()(self.get_architecture_spec)
        self.mcp.tool()(self.validate_architecture_compliance)
        self.mcp.tool()(self.apply_architectural_remediation)

    async def get_architecture_spec(self) -> str:
        """Retrieves the current project architectural specification (SPEC.md)."""
        try:
            spec_path = os.path.join(self.container.workspace_root, "SPEC.md")
            with open(spec_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "No SPEC.md found."

    async def validate_architecture_compliance(self) -> str:
        """Validates staged changes and returns a scorecard of NEW violations."""
        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        if not os.path.exists(rules_path):
            return "Missing rules.yaml. Run 'aegis init' first."

        rules = self.container.policy_parser.parse_rules(rules_path)
        violations = self.container.evaluation_service.evaluate_changes(rules)
        active = [v for v in violations if not self.container.baseline_manager.is_exempt(v)]
        
        if not active: return "✅ Compliance check passed."
        
        report = "[!] NEW Architectural Violations:\n"
        for v in active:
            report += f"- [{v.severity}] {v.file}:{v.line} - {v.description}\n"
        return report

    async def apply_architectural_remediation(self, rule_id: Optional[str] = None) -> str:
        """
        Automates the resolution of architectural violations.
        Returns a summary of applied remediation plans.
        """
        rules_path = os.path.join(self.container.workspace_root, ".aegis", "rules.yaml")
        if not os.path.exists(rules_path):
            return "Missing rules.yaml."

        rules = self.container.policy_parser.parse_rules(rules_path)
        if rule_id:
            rules = [r for r in rules if r.id == rule_id]

        violations = self.container.evaluation_service.evaluate_workspace(".", rules)
        active = [v for v in violations if not self.container.baseline_manager.is_exempt(v)]
        
        if not active: return "No active violations requiring remediation."
        
        plan = self.container.remediation_service.create_plan(active)
        success_count = self.container.remediation_service.execute_plan(plan)
        
        return f"✅ Remediation Success: Applied {success_count} fixes out of {len(active)} detected violations."

    def run(self):
        self.mcp.run()

def main():
    kernel = AegisKernel()
    kernel.run()

if __name__ == "__main__":
    main()
