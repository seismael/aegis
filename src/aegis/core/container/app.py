import os
from collections.abc import Callable
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from aegis.domain.policy.pack_manager import RulePackManager

from aegis.core.container.config_loader import load_aegis_config
from aegis.core.models.config import AegisConfig
from aegis.core.plugins.registry import PluginRegistry
from aegis.domain.enforcement.remediation import RemediationPromptSynthesizer
from aegis.domain.evaluation.baseline import BaselineManager
from aegis.domain.evaluation.service import EvaluationService
from aegis.domain.evolution.service import EvolutionService
from aegis.domain.governance.service import GovernanceService
from aegis.domain.policy.models import (
    CategoryPhaseMapping,
    EvaluationPhase,
    RuleCategory,
)
from aegis.domain.policy.parser import PolicyParser
from aegis.infrastructure.ast_analyzer import TreeSitterAnalyzer
from aegis.infrastructure.git_provider import GitDiffProvider
from aegis.infrastructure.graph_analyzer import GraphAnalyzer
from aegis.infrastructure.regex_analyzer import RegexAnalyzer

logger = structlog.get_logger()

# Timeout for calls to degraded or uninitialized components.
_DEGRADED_SENTINEL = object()


class Container:
    """
    Composition Root for the Aegis application.
    Manages dependency injection and shared component lifecycles.
    """

    def __init__(self, workspace_root: str | None = None):
        self._init_errors: list[str] = []
        self.workspace_root = workspace_root or self._discover_project_root()

        # Configuration
        self._aegis_config: AegisConfig = load_aegis_config(self.workspace_root)
        self._telemetry_recorder_cache = None

        # Infrastructure — Analyzers (always safe to construct)
        self.tree_sitter_analyzer = TreeSitterAnalyzer()
        self.graph_analyzer = GraphAnalyzer()
        self.regex_analyzer = RegexAnalyzer()

        # Git provider (handles missing repo internally)
        self.diff_provider = self._try_init(
            "diff_provider", GitDiffProvider, self.workspace_root
        )

        # Baseline manager (may fail on permissions)
        self.baseline_manager = self._try_init(
            "baseline_manager",
            BaselineManager,
            os.path.join(self.workspace_root, ".aegis"),
        )

        # Plugins (discovered at boot)
        self.plugin_registry = PluginRegistry(self.workspace_root)
        try:
            self.plugin_registry.load_plugins()
        except Exception as exc:
            self._record_init_error(f"plugins: {exc}")

        # Evaluation service (requires baseline manager)
        self.evaluation_service = self._build_evaluation_service()

        self.policy_parser = PolicyParser(
            cache_dir=os.path.join(self.workspace_root, ".aegis", "cache")
        )
        self._rule_pack_manager: RulePackManager | None = None
        self._cached_rules: list | None = None

        # Evolution (may fail on permissions)
        self.evolution_service = self._try_init(
            "evolution_service",
            EvolutionService,
            os.path.join(self.workspace_root, ".aegis"),
        )

        # Remediation
        self.remediation_synthesizer = RemediationPromptSynthesizer(
            extra_analyzers=self.plugin_registry.custom_analyzers
        )

        # Governance orchestration
        self.governance_service = self._build_governance_service()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def rule_pack_manager(self) -> "RulePackManager":
        """Lazily-initialized pack manager for rule lifecycle operations."""
        if self._rule_pack_manager is None:
            from aegis.domain.policy.pack_manager import RulePackManager

            rules_dir = os.path.join(self.workspace_root, ".aegis", "rules")
            self._rule_pack_manager = RulePackManager(rules_dir)
        return self._rule_pack_manager

    @property
    def custom_mcp_tools(self) -> list[Callable]:
        return list(self.plugin_registry.custom_mcp_tools)

    @property
    def loaded_plugins(self) -> list[str]:
        return self.plugin_registry.loaded_plugins

    @property
    def telemetry_recorder(self):
        """Lazy TelemetryRecorder for architectural observability."""
        if self._telemetry_recorder_cache is _DEGRADED_SENTINEL:
            return None
        if self._telemetry_recorder_cache is not None:
            return self._telemetry_recorder_cache
        try:
            from aegis.domain.observability.telemetry import (
                TelemetryRecorder,
            )

            self._telemetry_recorder_cache = TelemetryRecorder(self.workspace_root)
            return self._telemetry_recorder_cache
        except Exception as exc:
            self._telemetry_recorder_cache = _DEGRADED_SENTINEL
            self._record_init_error(f"telemetry_recorder: {exc}")
            return None

    @property
    def init_errors(self) -> list[str]:
        """Messages describing which components failed to initialise."""
        return list(self._init_errors)

    def is_degraded(self) -> bool:
        """True when at least one non-critical component failed to initialise."""
        return len(self._init_errors) > 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_init(self, name: str, factory: type, *args, **kwargs) -> object:
        """Attempt to construct *factory*, logging & recording on failure."""
        try:
            return factory(*args, **kwargs)
        except Exception as exc:
            self._record_init_error(f"{name}: {exc}")
            return None

    def _record_init_error(self, msg: str) -> None:
        self._init_errors.append(msg)
        logger.warning("Container init degraded", error=msg)

    def _build_evaluation_service(self) -> EvaluationService | None:
        if not self.baseline_manager:
            self._record_init_error("evaluation_service: baseline_manager unavailable")
            return None
        try:
            return EvaluationService(
                self.tree_sitter_analyzer,
                self.graph_analyzer,
                self.regex_analyzer,
                self.diff_provider,
                extra_analyzers=self.plugin_registry.custom_analyzers,
            )
        except Exception as exc:
            self._record_init_error(f"evaluation_service: {exc}")
            return None

    def _build_governance_service(self) -> GovernanceService | None:
        if not self.evaluation_service or not self.baseline_manager:
            self._record_init_error(
                "governance_service: missing dependency "
                "(evaluation_service or baseline_manager)"
            )
            return None
        try:
            return GovernanceService(self.evaluation_service, self.baseline_manager)
        except Exception as exc:
            self._record_init_error(f"governance_service: {exc}")
            return None

    def load_rules(self) -> list:
        """
        Loads rules from the .aegis/rules/ directory
        and auto-registered plugin rules.  Cached for idempotency.
        """
        if self._cached_rules is not None:
            return self._cached_rules

        rules_dir = os.path.join(self.workspace_root, ".aegis", "rules")
        rules = []
        if os.path.isdir(rules_dir):
            rules = self.policy_parser.parse_directory(rules_dir)

        # Add auto-registered rules from plugins
        if self.plugin_registry:
            rules.extend(self.plugin_registry.auto_rules)

        self._cached_rules = rules
        return rules

    @property
    def category_phase_mapping(self) -> CategoryPhaseMapping:
        """Default phase mapping merged with config overrides."""
        base = CategoryPhaseMapping()
        if self._aegis_config and self._aegis_config.phase_defaults:
            for cat_name, phases in self._aegis_config.phase_defaults.items():
                try:
                    cat = RuleCategory(cat_name)
                    base.category_defaults[cat] = [EvaluationPhase(p) for p in phases]
                except (ValueError, TypeError):
                    continue
        # category_overrides take precedence over phase_defaults
        if self._aegis_config and self._aegis_config.category_overrides:
            for cat_name, phases in self._aegis_config.category_overrides.items():
                try:
                    cat = RuleCategory(cat_name)
                    base.category_defaults[cat] = [EvaluationPhase(p) for p in phases]
                except (ValueError, TypeError):
                    continue
        return base

    def load_rules_for_phase(
        self,
        phase: str | None = None,
        category: str | None = None,
    ) -> list:
        """Load rules and optionally filter by phase and/or category.

        Returns all rules when no filters are provided (backward compatible).
        """
        all_rules = self.load_rules()
        mapping = self.category_phase_mapping
        phase_enum = EvaluationPhase(phase) if phase else None
        cat_enum = RuleCategory(category) if category else None

        return EvaluationService.filter_rules_by_phase(
            all_rules, phase=phase_enum, category=cat_enum, phase_mapping=mapping
        )

    def _discover_project_root(self) -> str:
        """
        Scans upwards for pyproject.toml or .git to identify the project root.
        Defaults to CWD if nothing found.
        """
        current = os.getcwd()
        while current != os.path.dirname(current):
            if os.path.exists(
                os.path.join(current, "pyproject.toml")
            ) or os.path.exists(os.path.join(current, ".git")):
                return current
            current = os.path.dirname(current)
        return os.getcwd()
