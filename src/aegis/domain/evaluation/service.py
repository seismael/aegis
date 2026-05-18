import os

import structlog

from aegis.core.constants import IGNORE_DIRS
from aegis.domain.evaluation.ports import (
    ArchitecturalViolation,
    DiffProviderInterface,
    GraphAnalyzerInterface,
    RegexAnalyzerInterface,
    RuleAnalyzerInterface,
)
from aegis.domain.evaluation.scoping import ScopeFilter
from aegis.domain.policy.models import (
    CategoryPhaseMapping,
    EngineType,
    EvaluationPhase,
    Rule,
    RuleCategory,
)

logger = structlog.get_logger()


class EvaluationService:
    """
    Coordinates architectural analysis across the workspace.
    Routes rules to the correct analyzer based on engine_type.
    Supports both full sweeps and token-efficient diff-based analysis.
    """

    def __init__(
        self,
        tree_sitter_analyzer: RuleAnalyzerInterface,
        graph_analyzer: GraphAnalyzerInterface,
        regex_analyzer: RegexAnalyzerInterface,
        diff_provider: DiffProviderInterface,
        extra_analyzers: list[RuleAnalyzerInterface] | None = None,
    ):
        self.tree_sitter_analyzer = tree_sitter_analyzer
        self.graph_analyzer = graph_analyzer
        self.regex_analyzer = regex_analyzer
        self.diff_provider = diff_provider
        self.extra_analyzers = extra_analyzers or []

    def evaluate_workspace(
        self,
        root_dir: str,
        rules: list[Rule],
        phase: EvaluationPhase | None = None,
        category: RuleCategory | None = None,
        phase_mapping: CategoryPhaseMapping | None = None,
    ) -> list[ArchitecturalViolation]:
        """
        Performs a full architectural sweep of the workspace.
        Routes file-level rules (tree-sitter, regex) per-file
        and graph-level rules once across the workspace.
        """
        rules = self.filter_rules_by_phase(rules, phase, category, phase_mapping)
        all_violations: list[ArchitecturalViolation] = []

        # Lifecycle hook: Start
        for extra in self.extra_analyzers:
            if hasattr(extra, "on_evaluation_start"):
                extra.on_evaluation_start(root_dir)

        # Partition rules by engine type
        ts_rules = [r for r in rules if r.engine_type == EngineType.TREE_SITTER]
        regex_rules = [r for r in rules if r.engine_type == EngineType.REGEX]
        graph_rules = [r for r in rules if r.engine_type == EngineType.GRAPH]

        # File-level analysis (tree-sitter + regex + extra analyzers)
        if ts_rules or regex_rules or self.extra_analyzers:
            for root, _, files in os.walk(root_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if any(x in file_path.split(os.sep) for x in IGNORE_DIRS):
                        continue

                    try:
                        with open(file_path, encoding="utf-8") as f:
                            content = f.read()

                        if ts_rules:
                            all_violations.extend(
                                self.tree_sitter_analyzer.analyze_file(
                                    file_path, content, ts_rules
                                )
                            )
                        if regex_rules:
                            all_violations.extend(
                                self.regex_analyzer.analyze_file(
                                    file_path, content, regex_rules
                                )
                            )
                        for extra in self.extra_analyzers:
                            all_violations.extend(
                                extra.analyze_file(file_path, content, rules)
                            )
                    except (UnicodeDecodeError, OSError):
                        continue

        # Cross-file graph analysis (once per sweep)
        if graph_rules:
            all_violations.extend(
                self.graph_analyzer.analyze_graph(root_dir, graph_rules)
            )

        # Hook: Project-wide analysis
        for extra in self.extra_analyzers:
            if hasattr(extra, "analyze_project"):
                all_violations.extend(extra.analyze_project(root_dir, rules))

        # Normalize paths to relative for consistent baseline matching
        self._normalize_violation_paths(all_violations, root_dir)

        # Lifecycle hook: End
        for extra in self.extra_analyzers:
            if hasattr(extra, "on_evaluation_end"):
                extra.on_evaluation_end(all_violations)

        return ScopeFilter.filter_violations(all_violations, rules)

    @staticmethod
    def _normalize_violation_paths(
        violations: list[ArchitecturalViolation], root_dir: str
    ) -> None:
        """Normalize absolute paths to relative for consistent baseline matching."""
        for v in violations:
            if os.path.isabs(v.file):
                try:
                    v.file = os.path.relpath(v.file, root_dir)
                except ValueError:
                    pass  # different drive, keep as-is

    @staticmethod
    def filter_rules_by_phase(
        rules: list[Rule],
        phase: EvaluationPhase | None = None,
        category: RuleCategory | None = None,
        phase_mapping: CategoryPhaseMapping | None = None,
    ) -> list[Rule]:
        """Filter rules by evaluation phase and/or category.

        - When *phase* is None, all rules pass (backward compatible).
        - When *phase* is set, rules pass if their explicit ``phases``
          contain the phase, or their category's default mapping includes it.
        - When *category* is set, only rules of that category pass.
        - Both filters can be combined (AND logic).
        """
        mapping = phase_mapping or CategoryPhaseMapping()

        def _matches(r: Rule) -> bool:
            if category is not None and r.category != category:
                return False
            if phase is None:
                return True
            # Explicit phases on the rule take priority
            if r.phases is not None:
                return phase in r.phases
            # Fall back to category default mapping
            return phase in mapping.category_defaults.get(
                r.category, [EvaluationPhase.ON_DEMAND]
            )

        return [r for r in rules if _matches(r)]

    def evaluate_changes(
        self,
        rules: list[Rule],
        root_dir: str | None = None,
        phase: EvaluationPhase | None = None,
        category: RuleCategory | None = None,
        phase_mapping: CategoryPhaseMapping | None = None,
    ) -> list[ArchitecturalViolation]:
        """
        Performs a token-efficient analysis of only the changed lines in changed files.
        Graph rules are skipped (cross-file analysis requires a full workspace sweep).
        """
        rules = self.filter_rules_by_phase(rules, phase, category, phase_mapping)

        if not self.diff_provider:
            logger.warning(
                "evaluate_changes: diff_provider unavailable (not a git repo?)"
            )
            return []

        diff = self.diff_provider.get_staged_changes()
        all_violations: list[ArchitecturalViolation] = []

        # Derive root_dir from first changed file if not provided
        root_dir = root_dir or self._derive_root_dir(diff.changed_files)

        # Partition rules
        ts_rules = [r for r in rules if r.engine_type == EngineType.TREE_SITTER]
        regex_rules = [r for r in rules if r.engine_type == EngineType.REGEX]
        graph_rules = [r for r in rules if r.engine_type == EngineType.GRAPH]

        if graph_rules:
            logger.debug(
                "Graph rules skipped during staged evaluation "
                "(requires full workspace sweep).",
                rule_count=len(graph_rules),
            )

        if not ts_rules and not regex_rules and not self.extra_analyzers:
            return all_violations

        for file_path in diff.changed_files:
            try:
                if not os.path.exists(file_path):
                    continue

                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                file_violations: list[ArchitecturalViolation] = []
                if ts_rules:
                    file_violations.extend(
                        self.tree_sitter_analyzer.analyze_file(
                            file_path, content, ts_rules
                        )
                    )
                if regex_rules:
                    file_violations.extend(
                        self.regex_analyzer.analyze_file(
                            file_path, content, regex_rules
                        )
                    )
                for extra in self.extra_analyzers:
                    file_violations.extend(
                        extra.analyze_file(file_path, content, rules)
                    )

                modified_lines = diff.get_modified_lines(file_path)
                if modified_lines:
                    file_violations = [
                        v for v in file_violations if v.line in modified_lines
                    ]

                all_violations.extend(file_violations)
            except Exception as e:
                logger.error(
                    "Failed to analyze changed file",
                    file=file_path,
                    error=str(e),
                )

        # Normalize paths to relative for consistent baseline matching
        self._normalize_violation_paths(all_violations, root_dir)

        return ScopeFilter.filter_violations(all_violations, rules)

    @staticmethod
    def _derive_root_dir(changed_files: set[str]) -> str:
        """Derive the workspace root from a set of changed file paths."""
        if not changed_files:
            return os.getcwd()
        try:
            common = os.path.commonpath(list(changed_files))
        except ValueError:
            return os.getcwd()
        # If common is a file path (single file diff), use its parent
        if common and not os.path.isdir(common):
            common = os.path.dirname(common)
        return common or os.getcwd()
