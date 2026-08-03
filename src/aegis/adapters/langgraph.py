"""
LangGraph Ecosystem Adapter for Aegis Runtime.

Constructs native LangGraph StateGraph topologies hardened by Aegis PlanVerifier,
EnforcementNode, and NativeAegisExecutor.
"""

from collections.abc import Callable
from typing import Any

from aegis.core.baseline import BaselineManager
from aegis.core.parser import TreeSitterAnalyzer
from aegis.core.registry import Rule
from aegis.domain.evaluation.analyzers.graph import GraphAnalyzer
from aegis.domain.evaluation.analyzers.regex import RegexAnalyzer
from aegis.domain.evaluation.analyzers.semantic import SemanticAnalyzer
from aegis.domain.evaluation_service import EvaluationService
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

        self.plan_verifier = AegisPlanVerifier(self.rules)
        self.enforcement_node = AegisEnforcementNode(
            self.evaluation, self.rules, self.baseline
        )
        self.final_gate = AegisFinalGate(self.rules)
        self.executor = NativeAegisExecutor(self.evaluation, self.rules)

    def run_step(
        self, state: AegisState, tool_fn: Callable[..., Any] | None = None
    ) -> AegisState:
        """
        Executes a single state transition through the governed graph topology.
        """
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

        pending = state.get("pending_tool_call")
        if pending:
            update = self.enforcement_node(state)
            if not update["governance_valid"]:
                return {**state, **update}

            if tool_fn and pending.get("name"):
                tool_name = pending["name"]
                tool_args = (
                    pending.get("args")
                    if "args" in pending
                    else {k: v for k, v in pending.items() if k != "name"}
                )
                res = self.executor.execute_tool(tool_name, tool_args, tool_fn)
                return {
                    **state,
                    **update,
                    "tool_output": res,
                }

        return {**state, "governance_valid": True}


class LangGraphAdapter:
    """
    LangGraph Ecosystem Adapter for Aegis Runtime.

    Composes a GovernedExecutionGraph for native LangGraph StateGraph
    integration. Provides framework-specific state management
    and graph topology configuration.
    """

    def __init__(
        self,
        rules: list[Rule],
        workspace_root: str = ".",
        evaluation_service: EvaluationService | None = None,
    ):
        self._graph = GovernedExecutionGraph(
            rules=rules,
            workspace_root=workspace_root,
            evaluation_service=evaluation_service,
        )

    def run_step(
        self, state: AegisState, tool_fn: Callable[..., Any] | None = None
    ) -> AegisState:
        """
        Executes a single state transition through the governed graph topology.
        """
        return self._graph.run_step(state, tool_fn)

    def build_state_graph(self):
        """
        Build a native LangGraph StateGraph with Aegis governance nodes baked in.
        Returns a compiled graph: START -> plan_verifier -> enforcement -> tools -> END
        """
        from langgraph.graph import END, StateGraph

        from aegis.runtime.state import AegisState

        graph = StateGraph(AegisState)
        graph.add_node("plan_verifier", self._graph.plan_verifier)
        graph.add_node("enforcement", self._graph.enforcement_node)
        graph.add_node("final_gate", self._graph.final_gate)
        graph.set_entry_point("plan_verifier")
        graph.add_conditional_edges(
            "plan_verifier",
            lambda state: "enforcement" if state.get("governance_valid") else END,
        )
        graph.add_edge("enforcement", "final_gate")
        graph.add_edge("final_gate", END)
        return graph.compile()


__all__ = [
    "LangGraphAdapter",
    "GovernedExecutionGraph",
    "AegisPlanVerifier",
    "AegisEnforcementNode",
    "AegisFinalGate",
]
