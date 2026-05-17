import os
from pathlib import PurePosixPath

import structlog

from aegis.core.models.governance import EngineType, Rule
from aegis.domain.evaluation.ports import (
    ASTAnalyzerInterface,
    ASTViolation,
    DiffProviderInterface,
    GraphAnalyzerInterface,
    RegexAnalyzerInterface,
)

logger = structlog.get_logger()

IGNORE_DIRS = {".venv", "node_modules", ".git", ".aegis", "__pycache__"}


class EvaluationService:
    """
    Coordinates architectural analysis across the workspace.
    Routes rules to the correct analyzer based on engine_type.
    Supports both full sweeps and token-efficient diff-based analysis.
    """

    def __init__(
        self,
        tree_sitter_analyzer: ASTAnalyzerInterface,
        graph_analyzer: GraphAnalyzerInterface,
        regex_analyzer: RegexAnalyzerInterface,
        diff_provider: DiffProviderInterface,
        extra_analyzers: list[ASTAnalyzerInterface] | None = None,
    ):
        self.tree_sitter_analyzer = tree_sitter_analyzer
        self.graph_analyzer = graph_analyzer
        self.regex_analyzer = regex_analyzer
        self.diff_provider = diff_provider
        self.extra_analyzers = extra_analyzers or []

    def evaluate_workspace(
        self, root_dir: str, rules: list[Rule]
    ) -> list[ASTViolation]:
        """
        Performs a full architectural sweep of the workspace.
        Routes file-level rules (tree-sitter, regex) per-file
        and graph-level rules once across the workspace.
        """
        all_violations: list[ASTViolation] = []

        # Partition rules by engine type
        ts_rules = [r for r in rules if r.engine_type == EngineType.TREE_SITTER]
        regex_rules = [r for r in rules if r.engine_type == EngineType.REGEX]
        graph_rules = [r for r in rules if r.engine_type == EngineType.GRAPH]

        # File-level analysis (tree-sitter + regex + extra analyzers)
        if ts_rules or regex_rules or self.extra_analyzers:
            for root, _, files in os.walk(root_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if any(x in file_path for x in IGNORE_DIRS):
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
                    except (UnicodeDecodeError, PermissionError):
                        continue

        # Cross-file graph analysis (once per sweep)
        if graph_rules:
            all_violations.extend(
                self.graph_analyzer.analyze_graph(root_dir, graph_rules)
            )

        return self._filter_excluded(all_violations, rules)

    @staticmethod
    def _filter_excluded(
        violations: list[ASTViolation], rules: list[Rule]
    ) -> list[ASTViolation]:
        """Keep violations where file matches rule's applies_to and not in excludes."""
        rule_map = {r.id: r for r in rules}
        filtered: list[ASTViolation] = []
        for v in violations:
            rule = rule_map.get(v.rule_id)
            if not rule:
                filtered.append(v)
                continue

            pp = PurePosixPath(v.file.replace("\\", "/"))

            # Positive filter: must match at least one applies_to pattern
            if rule.applies_to:
                allowed = any(pp.match(p) for p in rule.applies_to)
                if not allowed:
                    continue

            # Negative filter: must not match any excludes pattern
            if rule.excludes:
                excluded = any(pp.match(p) for p in rule.excludes)
                if excluded:
                    continue

            filtered.append(v)
        return filtered

    def evaluate_changes(self, rules: list[Rule]) -> list[ASTViolation]:
        """
        Performs a token-efficient analysis of only the changed lines in changed files.
        Graph rules are skipped (cross-file analysis requires a full workspace sweep).
        """
        diff = self.diff_provider.get_staged_changes()
        all_violations: list[ASTViolation] = []

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
                full_path = (
                    os.path.join(self.diff_provider.repo.working_dir, file_path)
                    if hasattr(self.diff_provider, "repo") and self.diff_provider.repo
                    else file_path
                )

                if not os.path.exists(full_path):
                    continue

                with open(full_path, encoding="utf-8") as f:
                    content = f.read()

                file_violations: list[ASTViolation] = []
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

        return self._filter_excluded(all_violations, rules)
