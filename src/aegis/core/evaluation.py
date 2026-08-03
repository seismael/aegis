"""
Aegis Core Evaluation Service.
Orchestrates Tree-sitter, Graph, Regex, and Semantic analyzers natively.
Zero agent-framework dependencies.
"""

import difflib
import os
import re

import structlog

from aegis.core.analyzers.graph import GraphAnalyzer, GraphAnalyzerInterface
from aegis.core.analyzers.regex import RegexAnalyzer, RegexAnalyzerInterface
from aegis.core.analyzers.semantic import SemanticAnalyzer, SemanticAnalyzerInterface
from aegis.core.parser import RuleAnalyzerInterface, TreeSitterAnalyzer
from aegis.core.registry import (
    ArchitecturalViolation,
    CategoryPhaseMapping,
    EngineType,
    EvaluationPhase,
    Rule,
    RuleCategory,
)
from aegis.core.scoping import IGNORE_DIRS, LANG_EXT_MAP, ScopeFilter

logger = structlog.get_logger()



class EvaluationService:
    """
    Coordinates architectural analysis across the workspace.
    Routes rules to the correct analyzer based on engine_type.
    Supports both full sweeps and token-efficient diff-based analysis.
    """

    def __init__(
        self,
        tree_sitter_analyzer: RuleAnalyzerInterface | None = None,
        graph_analyzer: GraphAnalyzerInterface | None = None,
        regex_analyzer: RegexAnalyzerInterface | None = None,
        semantic_analyzer: SemanticAnalyzerInterface | None = None,
        extra_analyzers: list[RuleAnalyzerInterface] | None = None,
    ):
        self.tree_sitter_analyzer = tree_sitter_analyzer or TreeSitterAnalyzer()
        self.graph_analyzer = graph_analyzer or GraphAnalyzer()
        self.regex_analyzer = regex_analyzer or RegexAnalyzer()
        self.semantic_analyzer = semantic_analyzer or SemanticAnalyzer()
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
        if not rules:
            return []

        all_violations: list[ArchitecturalViolation] = []

        for extra in self.extra_analyzers:
            try:
                if hasattr(extra, "on_evaluation_start"):
                    extra.on_evaluation_start(root_dir)
            except Exception:
                logger.warning(
                    "Plugin on_evaluation_start failed",
                    plugin=type(extra).__name__,
                )

        ts_rules = [r for r in rules if r.engine_type == EngineType.TREE_SITTER]
        regex_rules = [r for r in rules if r.engine_type == EngineType.REGEX]
        graph_rules = [r for r in rules if r.engine_type == EngineType.GRAPH]
        semantic_rules = [r for r in rules if r.engine_type == EngineType.SEMANTIC]

        if ts_rules or regex_rules or semantic_rules or self.extra_analyzers:
            for root, _, files in os.walk(root_dir):
                rel_root = os.path.relpath(root, root_dir)
                if rel_root != "." and any(
                    x in rel_root.split(os.sep) for x in IGNORE_DIRS
                ):
                    continue
                for file in files:
                    if file in IGNORE_DIRS:
                        continue
                    file_path = os.path.join(root, file)

                    try:
                        content = self._get_file_content(file_path)

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
                        if semantic_rules and self.semantic_analyzer:
                            all_violations.extend(
                                self.semantic_analyzer.analyze_semantic(
                                    file_path, content, semantic_rules
                                )
                            )
                        for extra in self.extra_analyzers:
                            try:
                                all_violations.extend(
                                    extra.analyze_file(file_path, content, rules)
                                )
                            except Exception:
                                logger.warning(
                                    "Plugin analyze_file failed",
                                    plugin=type(extra).__name__,
                                    file=file_path,
                                )
                    except (UnicodeDecodeError, OSError, FileNotFoundError):
                        continue

        if graph_rules:
            all_violations.extend(
                self.graph_analyzer.analyze_graph(root_dir, graph_rules)
            )

        for extra in self.extra_analyzers:
            try:
                if hasattr(extra, "analyze_project"):
                    all_violations.extend(extra.analyze_project(root_dir, rules))
            except Exception:
                logger.warning(
                    "Plugin analyze_project failed",
                    plugin=type(extra).__name__,
                )

        self._normalize_violation_paths(all_violations, root_dir)

        rules_map = {r.id: r for r in rules}
        for v in all_violations:
            rule = rules_map.get(v.rule_id)
            if rule:
                v.proposed_patch = self._generate_patch(v, rule, root_dir)

        for extra in self.extra_analyzers:
            try:
                if hasattr(extra, "on_evaluation_end"):
                    extra.on_evaluation_end(all_violations)
            except Exception:
                logger.warning(
                    "Plugin on_evaluation_end failed",
                    plugin=type(extra).__name__,
                )

        return ScopeFilter.filter_violations(all_violations, rules)

    @staticmethod
    def _normalize_violation_paths(
        violations: list[ArchitecturalViolation], root_dir: str
    ) -> None:
        """Normalize absolute paths to relative for consistent baseline matching."""
        for v in violations:
            if os.path.isabs(v.file):
                try:
                    rel = os.path.relpath(v.file, root_dir)
                    v.file = rel.replace("\\", "/").replace(os.sep, "/")
                except ValueError:
                    pass
            else:
                v.file = v.file.replace("\\", "/").replace(os.sep, "/")

    @staticmethod
    def filter_rules_by_phase(
        rules: list[Rule],
        phase: EvaluationPhase | None = None,
        category: RuleCategory | None = None,
        phase_mapping: CategoryPhaseMapping | None = None,
    ) -> list[Rule]:
        """Filter rules by evaluation phase and/or category."""
        mapping = phase_mapping or CategoryPhaseMapping()

        def _matches(r: Rule) -> bool:
            if category is not None and r.category != category:
                return False
            if phase is None:
                return True
            if r.phases is not None:
                return phase in r.phases
            return phase in mapping.category_defaults.get(
                r.category, [EvaluationPhase.ON_DEMAND]
            )

        return [r for r in rules if _matches(r)]

    def evaluate_code_string(
        self, code_string: str, language: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        """Evaluate a code string in-memory against applicable rules."""
        if not code_string or not rules:
            return []

        ext = LANG_EXT_MAP.get(language, f".{language}")
        synthetic_path = f"memory{ext}"

        lang_rules = [r for r in rules if r.language == language]
        if not lang_rules:
            return []

        violations: list[ArchitecturalViolation] = []

        ts_rules = [r for r in lang_rules if r.engine_type == EngineType.TREE_SITTER]
        regex_rules = [r for r in lang_rules if r.engine_type == EngineType.REGEX]

        if ts_rules:
            try:
                violations.extend(
                    self.tree_sitter_analyzer.analyze_file(
                        synthetic_path, code_string, ts_rules
                    )
                )
            except Exception:
                pass

        if regex_rules:
            try:
                violations.extend(
                    self.regex_analyzer.analyze_file(
                        synthetic_path, code_string, regex_rules
                    )
                )
            except Exception:
                pass

        rules_map = {r.id: r for r in rules}
        for v in violations:
            rule = rules_map.get(v.rule_id)
            if rule:
                v.proposed_patch = self._generate_patch(
                    v, rule, code_string=code_string
                )

        return violations

    def evaluate_file(
        self,
        file_path: str,
        rules: list[Rule],
        root_dir: str | None = None,
    ) -> list[ArchitecturalViolation]:
        """Evaluate a single file against applicable rules."""
        file_violations: list[ArchitecturalViolation] = []
        try:
            content = self._get_file_content(file_path)
        except (UnicodeDecodeError, OSError, FileNotFoundError):
            return file_violations

        ts_rules = [r for r in rules if r.engine_type == EngineType.TREE_SITTER]
        regex_rules = [r for r in rules if r.engine_type == EngineType.REGEX]

        if ts_rules:
            file_violations.extend(
                self.tree_sitter_analyzer.analyze_file(file_path, content, ts_rules)
            )
        if regex_rules:
            file_violations.extend(
                self.regex_analyzer.analyze_file(file_path, content, regex_rules)
            )
        for extra in self.extra_analyzers:
            file_violations.extend(extra.analyze_file(file_path, content, rules))

        root_dir = root_dir or os.path.dirname(file_path)
        self._normalize_violation_paths(file_violations, root_dir)

        rules_map = {r.id: r for r in rules}
        for v in file_violations:
            rule = rules_map.get(v.rule_id)
            if rule:
                v.proposed_patch = self._generate_patch(v, rule, root_dir)

        return ScopeFilter.filter_violations(file_violations, rules)

    def _generate_patch(
        self,
        violation: ArchitecturalViolation,
        rule: Rule,
        root_dir: str | None = None,
        code_string: str | None = None,
    ) -> str | None:
        """Generates a unified diff patch for a violation if a replacement is known."""
        suggested_replacement = rule.metadata.get("suggested_replacement")
        if not suggested_replacement:
            return None

        original_content = code_string
        if original_content is None:
            file_path = violation.file
            if root_dir and not os.path.isabs(file_path):
                file_path = os.path.join(root_dir, file_path)
            try:
                original_content = self._get_file_content(file_path)
            except Exception:
                return None

        if not original_content:
            return None

        new_content = None
        if rule.engine_type == EngineType.REGEX and rule.query:
            new_content = self._apply_regex_replacement(
                original_content, rule.query, suggested_replacement, violation.line
            )

        if new_content and new_content != original_content:
            diff = difflib.unified_diff(
                original_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=violation.file,
                tofile=violation.file,
            )
            return "".join(diff)

        return None

    def _apply_regex_replacement(
        self, content: str, pattern: str, replacement: str, target_line: int
    ) -> str:
        """Applies a regex replacement ONLY on the target line."""
        lines = content.splitlines(keepends=True)
        if 1 <= target_line <= len(lines):
            line_idx = target_line - 1
            lines[line_idx] = re.sub(pattern, replacement, lines[line_idx])
        return "".join(lines)

    def _get_file_content(self, file_path: str) -> str:
        with open(file_path, encoding="utf-8") as f:
            return f.read()


__all__ = ["EvaluationService"]
