from abc import ABC, abstractmethod
from typing import List
from aegis.core.models.remediation import RemediationAction, RemediationPlan
from aegis.domain.enforcement.ports import RemediationStrategyInterface
from aegis.domain.evaluation.ports import ASTViolation

class RemediationService:
    """
    Orchestrates the remediation process.
    """
    def __init__(self, strategies: List[RemediationStrategyInterface]):
        self.strategies = {s.name: s for s in strategies}

    def create_plan(self, violations: List[ASTViolation]) -> RemediationPlan:
        actions = []
        for v in violations:
            # Logic to select best strategy per violation
            # For now, we'll default to 'agent_refactor'
            actions.append(RemediationAction(
                violation=v,
                strategy="agent_refactor",
                description=f"Refactor {v.file}:{v.line} to resolve {v.rule_id}"
            ))
        return RemediationPlan(actions=actions, total_violations=len(violations))

    def execute_plan(self, plan: RemediationPlan) -> int:
        success_count = 0
        for action in plan.actions:
            strategy = self.strategies.get(action.strategy)
            if strategy and strategy.apply_fix(action):
                success_count += 1
        return success_count
