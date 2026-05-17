import os
from typing import Optional, Callable, List
from aegis.domain.evaluation.service import EvaluationService
from aegis.domain.policy.parser import PolicyParser
from aegis.domain.evaluation.baseline import BaselineManager
from aegis.infrastructure.ast_analyzer import TreeSitterAnalyzer
from aegis.infrastructure.git_provider import GitDiffProvider
from aegis.infrastructure.graph_analyzer import GraphAnalyzer
from aegis.infrastructure.regex_analyzer import RegexAnalyzer
from aegis.domain.evolution.service import EvolutionService
from aegis.core.plugins.registry import PluginRegistry


class Container:
    """
    Composition Root for the Aegis application.
    Manages dependency injection and shared component lifecycles.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = workspace_root or self._discover_project_root()

        # Infrastructure — Analyzers
        self.tree_sitter_analyzer = TreeSitterAnalyzer()
        self.graph_analyzer = GraphAnalyzer()
        self.regex_analyzer = RegexAnalyzer()
        self.diff_provider = GitDiffProvider(self.workspace_root)
        self.baseline_manager = BaselineManager(
            os.path.join(self.workspace_root, ".aegis")
        )

        # Plugins (discovered at boot)
        self.plugin_registry = PluginRegistry(self.workspace_root)
        self.plugin_registry.load_plugins()

        # Domain Services
        self.evaluation_service = EvaluationService(
            self.tree_sitter_analyzer,
            self.graph_analyzer,
            self.regex_analyzer,
            self.diff_provider,
            extra_analyzers=self.plugin_registry.custom_analyzers,
        )
        self.policy_parser = PolicyParser()

        # Evolution
        self.evolution_service = EvolutionService(
            os.path.join(self.workspace_root, ".aegis")
        )

    @property
    def custom_mcp_tools(self) -> List[Callable]:
        return list(self.plugin_registry.custom_mcp_tools)

    def _discover_project_root(self) -> str:
        """
        Scans upwards for pyproject.toml or .git to identify the project root.
        Defaults to CWD if nothing found.
        """
        current = os.getcwd()
        while current != os.path.dirname(current):
            if os.path.exists(os.path.join(current, "pyproject.toml")) or os.path.exists(
                os.path.join(current, ".git")
            ):
                return current
            current = os.path.dirname(current)
        return os.getcwd()
