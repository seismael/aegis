"""
DeepAgents Ecosystem Adapter for Aegis Runtime.

Exposes DeepAgentsAdapter to seamlessly wrap DeepAgents / LangChain execution loops
with Aegis native governance nodes, enforcement executors, and self-correction loops.
"""

from collections.abc import Callable
from typing import Any

from aegis.agent import AegisAgent
from aegis.core import RegistryLoader, Rule
from aegis.domain import EvaluationService
from aegis.runtime.executor import AegisGovernanceError


class DeepAgentsAdapter(AegisAgent):
    """
    DeepAgents Native Governance Adapter.

    Integrates Aegis proactive verification, in-process AST delta compiler,
    and self-correction remediation loop natively into DeepAgents execution agents.
    """

    def __init__(
        self,
        rules: list[Rule] | None = None,
        workspace_root: str = ".",
        rules_file: str | None = None,
        evaluation_service: EvaluationService | None = None,
    ):
        if rules is None:
            if rules_file:
                loaded_rules = RegistryLoader.load_from_file(rules_file)
            else:
                loaded_rules = RegistryLoader.load(workspace_root)
        else:
            loaded_rules = rules

        super().__init__(
            rules=loaded_rules,
            workspace_root=workspace_root,
            evaluation_service=evaluation_service,
        )

    def run_governed_agent_loop(
        self,
        initial_request: str,
        code_generator_fn: Callable[[str], dict[str, Any]],
        tool_fn: Callable[..., Any],
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """
        Executes a native DeepAgents self-correction execution loop:
        1. Pre-flight intent verification (AegisPlanVerifier)
        2. In-memory AST delta evaluation (AegisEnforcementNode)
        3. Self-correction loop via RemediationPromptSynthesizer if violations found
        4. Sealed tool execution (NativeAegisExecutor) on clean payload
        """
        current_prompt = initial_request
        history: list[dict[str, Any]] = []

        for attempt in range(1, max_retries + 1):
            # Step 1: Generate proposed candidate payload from LLM/agent generator
            candidate = code_generator_fn(current_prompt)
            proposed_imports = candidate.get("proposed_imports")
            target_module = candidate.get("target_module")

            # Step 2: Pre-flight Plan Gate
            if proposed_imports and target_module:
                plan_res = self.verify_plan(proposed_imports, target_module)
                if not plan_res["plan_valid"]:
                    feedback = plan_res["feedback"]
                    history.append({"attempt": attempt, "stage": "plan_verifier", "feedback": feedback})
                    current_prompt = f"{initial_request}\n\n[AEGIS GOVERNANCE REJECTION - PRE-FLIGHT PLAN]\n{feedback}"
                    continue

            # Step 3: In-Memory AST Delta Compiler
            code_string = candidate.get("code") or candidate.get("content") or ""
            file_path = candidate.get("path") or candidate.get("file_path")
            language = candidate.get("language", "python")

            delta_res = self.evaluate_code_delta(code_string, language, file_path)
            if not delta_res["governance_valid"]:
                remediation = delta_res["remediation_prompt"]
                history.append({"attempt": attempt, "stage": "ast_enforcement", "remediation": remediation})
                current_prompt = f"{initial_request}\n\n[AEGIS GOVERNANCE INTERVENTION]\n{remediation}"
                continue

            # Step 4: Sealed Tool Execution
            try:
                output = self.execute_tool(
                    candidate.get("tool_name", "write_file"),
                    {"path": file_path, "content": code_string},
                    tool_fn,
                )
                return {
                    "success": True,
                    "attempts": attempt,
                    "output": output,
                    "history": history,
                }
            except AegisGovernanceError as err:
                history.append({"attempt": attempt, "stage": "executor", "error": str(err)})
                current_prompt = f"{initial_request}\n\n[AEGIS EXECUTOR BLOCK]\n{err}"

        return {
            "success": False,
            "attempts": max_retries,
            "error": "Max retries exceeded without achieving architectural compliance",
            "history": history,
        }


def create_deepagents_governed_agent(
    workspace_root: str = ".",
    rules: list[Rule] | None = None,
) -> DeepAgentsAdapter:
    """Factory helper to instantiate a DeepAgentsAdapter instance."""
    return DeepAgentsAdapter(rules=rules, workspace_root=workspace_root)


__all__ = ["DeepAgentsAdapter", "create_deepagents_governed_agent"]
