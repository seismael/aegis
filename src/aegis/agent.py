"""
AegisAgent Factory — Native Governance Agent Runtime.

Assembles in-process state machines integrating AegisPlanVerifier,
AegisEnforcementNode, and NativeAegisExecutor into a unified agent loop.
"""

from typing import Any

from aegis.core import (
    BaselineManager,
    GraphAnalyzer,
    RegexAnalyzer,
    Rule,
    SemanticAnalyzer,
    TreeSitterAnalyzer,
)
from aegis.domain import EvaluationService
from aegis.runtime.executor import NativeAegisExecutor
from aegis.runtime.nodes import AegisEnforcementNode, AegisFinalGate, AegisPlanVerifier


class AegisAgent:
    """
    Aegis Native Governance Agent Runtime.

    Encapsulates the proactive plan verifier, in-process AST enforcement node,
    hardened tool executor, and refinement loop in a single agent interface.
    """

    def __init__(
        self,
        rules: list[Rule],
        workspace_root: str = ".",
        evaluation_service: EvaluationService | None = None,
    ):
        self.rules = rules
        self.workspace_root = workspace_root

        if evaluation_service is None:
            self.evaluation = EvaluationService(
                tree_sitter_analyzer=TreeSitterAnalyzer(),
                graph_analyzer=GraphAnalyzer(),
                regex_analyzer=RegexAnalyzer(),
                semantic_analyzer=SemanticAnalyzer(),
            )
        else:
            self.evaluation = evaluation_service

        self.baseline = BaselineManager(f"{workspace_root}/.aegis")
        self.plan_verifier = AegisPlanVerifier(self.rules)
        self.enforcement_node = AegisEnforcementNode(
            self.evaluation, self.rules, self.baseline
        )
        self.final_gate = AegisFinalGate(self.rules)
        self.executor = NativeAegisExecutor(self.evaluation, self.rules)

    def verify_plan(self, proposed_imports: list[str], target_module: str) -> dict[str, Any]:
        """Proactively verify planning intent before code generation."""
        return self.plan_verifier.verify_plan(proposed_imports, target_module)

    def evaluate_code_delta(
        self,
        code_string: str,
        language: str = "python",
        file_path: str | None = None,
        rules: list[Rule] | None = None,
    ) -> dict[str, Any]:
        """In-process AST delta evaluation before disk write."""
        return self.enforcement_node.evaluate_delta(
            code_string, language, file_path, rules
        )

    def execute_tool(self, tool_name: str, tool_args: dict[str, Any], tool_fn: Any) -> Any:
        """Execute tool payload through the hardened executor."""
        return self.executor.execute_tool(tool_name, tool_args, tool_fn)


def create_aegis_agent(
    rules: list[Rule],
    workspace_root: str = ".",
    evaluation_service: EvaluationService | None = None,
) -> AegisAgent:
    """
    Factory function to instantiate an AegisAgent.

    Usage:
        agent = create_aegis_agent(rules, workspace_root)
        plan_res = agent.verify_plan(["aegis.infrastructure"], "aegis.domain.service")
        delta_res = agent.evaluate_code_delta("import os", "python")
    """
    return AegisAgent(
        rules=rules,
        workspace_root=workspace_root,
        evaluation_service=evaluation_service,
    )
