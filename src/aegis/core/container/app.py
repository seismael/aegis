import os
from typing import Optional
from aegis.domain.evaluation.service import EvaluationService
from aegis.domain.policy.parser import PolicyParser
from aegis.domain.evaluation.baseline import BaselineManager
from aegis.infrastructure.ast_analyzer import TreeSitterAnalyzer
from aegis.infrastructure.git_provider import GitDiffProvider
from aegis.domain.enforcement.remediation import RemediationService
from aegis.infrastructure.remediation_strategies import AgentRemediationStrategy
from aegis.domain.evolution.service import EvolutionService

class Container:
    """
    Composition Root for the Aegis application.
    Manages dependency injection and shared component lifecycles.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or self._discover_project_root()

        # Infrastructure
        self.analyzer = TreeSitterAnalyzer()
        self.diff_provider = GitDiffProvider(self.workspace_root)
        self.baseline_manager = BaselineManager(os.path.join(self.workspace_root, ".aegis"))

        # Domain Services
        self.evaluation_service = EvaluationService(self.analyzer, self.diff_provider)
        self.policy_parser = PolicyParser()

        # Remediation
        self.remediation_strategies = [AgentRemediationStrategy()]
        self.remediation_service = RemediationService(self.remediation_strategies)

        # Evolution
        self.evolution_service = EvolutionService(os.path.join(self.workspace_root, ".aegis"))

    def _discover_project_root(self) -> str:
        """
        Scans upwards for pyproject.toml or .git to identify the project root.
        Defaults to CWD if nothing found.
        """
        current = os.getcwd()
        while current != os.path.dirname(current):
            if os.path.exists(os.path.join(current, "pyproject.toml")) or \
               os.path.exists(os.path.join(current, ".git")):
                return current
            current = os.path.dirname(current)
        return os.getcwd()

