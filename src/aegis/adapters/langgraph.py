"""
LangGraph Ecosystem Adapter for Aegis Runtime.

Constructs native LangGraph StateGraph topologies hardened by Aegis PlanVerifier,
EnforcementNode, and NativeAegisExecutor.
"""

from collections.abc import Callable
from typing import Any

from aegis.core import Rule
from aegis.domain import EvaluationService
from aegis.domain.evaluation.analyzers.ast import TreeSitterAnalyzer
from aegis.domain.evaluation.analyzers.graph import GraphAnalyzer
from aegis.domain.evaluation.analyzers.regex import RegexAnalyzer
from aegis.domain.evaluation.analyzers.semantic import SemanticAnalyzer
from aegis.domain.evaluation.baseline import BaselineManager
from aegis.runtime.executor import NativeAegisExecutor
from aegis.runtime.nodes import AegisEnforcementNode, AegisFinalGate, AegisPlanVerifier
from aegis.runtime.state import AegisState


class GovernedExecutionGraph:
    """
    Native LangGraph StateGraph execution pipeline hardened by Aegis nodes.
    Simulates / wraps the state transition graph:
    [START] -> plan_verifier -> agent_gen -> enforcement_node -> [tools / END]
    """

    def __init__(
        self,
        rules: list[Rule],
        workspace_root: str = ".",
        evaluation_service: EvaluationService | None = None,
    ):
        self.rules = rules
        self.workspace_root = workspace_root
        self.evaluation = evaluation_service or EvaluationService(
            tree_sitter_analyzer=TreeSitterAnalyzer(),
            graph_analyzer=GraphAnalyzer(),
            regex_analyzer=RegexAnalyzer(),
            semantic_analyzer=SemanticAnalyzer(),
        )
        self.baseline = BaselineManager(f"{workspace_root}/.aegis")

        # Native Graph Nodes
        self.plan_verifier = AegisPlanVerifier(self.rules)
        self.enforcement_node = AegisEnforcementNode(
            self.evaluation, self.rules, self.baseline
        )
        self.final_gate = AegisFinalGate(self.rules)
        self.executor = NativeAegisExecutor(self.evaluation, self.rules)

    def run_step(self, state: AegisState, tool_fn: Callable[..., Any] | None = None) -> AegisState:
        """
        Executes a single state transition through the governed graph topology.
        """
        # Step 1: Pre-flight Plan Verification if proposed_imports present
        proposed_imports = state.get("proposed_imports")
        target_module = state.get("target_module")
        if proposed_imports and target_module:
            plan_res = self.plan_verifier.verify_plan(proposed_imports, target_module)
            if not plan_res["plan_valid"]:
                return {
                    **state,
                    "governance_valid": False,
                    "governance": [
                        {
                            "is_clean": False,
                            "total_violations": len(plan_res["violations"]),
                            "active_violations": plan_res["violations"],
                            "remediation_prompt": plan_res["feedback"],
                        }
                    ],
                }

        # Step 2: In-Memory AST Delta Evaluation on pending_tool_call
        pending = state.get("pending_tool_call")
        if pending:
            update = self.enforcement_node(state)
            if not update["governance_valid"]:
                return {**state, **update}

            # Step 3: Tool Execution if valid and tool_fn provided
            if tool_fn and pending.get("name"):
                tool_name = pending["name"]
                tool_args = pending.get("args") if "args" in pending else {k: v for k, v in pending.items() if k != "name"}
                res = self.executor.execute_tool(tool_name, tool_args, tool_fn)
                return {
                    **state,
                    **update,
                    "tool_output": res,
                }

        return {**state, "governance_valid": True}


class LangGraphAdapter(GovernedExecutionGraph):
    """LangGraph Ecosystem Adapter wrapper for Aegis Runtime."""
    pass


__all__ = [
    "LangGraphAdapter",
    "GovernedExecutionGraph",
    "AegisPlanVerifier",
    "AegisEnforcementNode",
    "AegisFinalGate",
]
