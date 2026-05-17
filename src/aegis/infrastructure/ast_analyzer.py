import hashlib
import importlib
from typing import Any

import structlog
from tree_sitter import Language, Parser, Query, QueryCursor

from aegis.core.models.governance import Rule
from aegis.domain.evaluation.ports import ASTAnalyzerInterface, ASTViolation

logger = structlog.get_logger()


class TreeSitterAnalyzer(ASTAnalyzerInterface):
    """
    Polyglot AST analyzer implementation using Tree-sitter.
    Supports dynamic language loading and structural signature hashing.
    """

    def __init__(self):
        self._languages: dict[str, Language] = {}
        self._parser_cache: dict[str, Parser] = {}
        self._tree_cache: dict[str, Any] = {}

        # Extension to package mapping
        self._lang_map = {
            "py": "tree_sitter_python",
            "ts": "tree_sitter_typescript",
            "tsx": "tree_sitter_typescript",
            "js": "tree_sitter_javascript",
            "jsx": "tree_sitter_javascript",
            "rs": "tree_sitter_rust",
        }

    def analyze_file(
        self, file_path: str, content: str, rules: list[Rule]
    ) -> list[ASTViolation]:
        ext = file_path.split(".")[-1].lower()

        # Filter rules by language
        relevant_rules = [r for r in rules if r.language == ext]
        if not relevant_rules:
            return []

        language = self._get_language(ext)
        if not language:
            return []

        if ext not in self._parser_cache:
            self._parser_cache[ext] = Parser(language)

        parser = self._parser_cache[ext]

        # Cache check
        content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()
        cache_key = f"{file_path}:{content_hash}"

        if cache_key in self._tree_cache:
            tree = self._tree_cache[cache_key]
        else:
            tree = parser.parse(bytes(content, "utf8"))
            self._tree_cache = {cache_key: tree}  # Minimal cache

        violations = []
        for rule in relevant_rules:
            try:
                # Handle standard query
                if rule.query:
                    query = Query(language, rule.query)
                    cursor = QueryCursor(query)
                    captures = cursor.captures(tree.root_node)

                    for name, nodes in captures.items():
                        for node in nodes:
                            violations.append(
                                self._create_violation(file_path, node, rule)
                            )

                # Handle positive rules (candidates - check)
                elif rule.candidates_query and rule.check_query:
                    c_query = Query(language, rule.candidates_query)
                    c_cursor = QueryCursor(c_query)
                    candidates = c_cursor.captures(tree.root_node)

                    compliance_query = Query(language, rule.check_query)
                    compliance_cursor = QueryCursor(compliance_query)
                    compliant = compliance_cursor.captures(tree.root_node)

                    compliant_points = set()
                    for nodes in compliant.values():
                        for node in nodes:
                            compliant_points.add(node.start_point)

                    for nodes in candidates.values():
                        for node in nodes:
                            if node.start_point not in compliant_points:
                                violations.append(
                                    self._create_violation(
                                        file_path,
                                        node,
                                        rule,
                                        desc=f"Compliance check failed: {rule.description}",
                                    )
                                )

            except Exception as exc:
                logger.debug(
                    "Tree-sitter query failed",
                    rule=rule.id,
                    file=file_path,
                    error=str(exc),
                )
                continue

        return violations

    def _get_language(self, ext: str) -> Language | None:
        if ext in self._languages:
            return self._languages[ext]

        pkg_name = self._lang_map.get(ext)
        if not pkg_name:
            return None

        try:
            # For tree-sitter-typescript, we need to handle multi-grammar packages
            if pkg_name == "tree_sitter_typescript":
                lang_func = importlib.import_module(pkg_name).language_typescript()
            else:
                lang_func = importlib.import_module(pkg_name).language()

            lang = Language(lang_func)
            self._languages[ext] = lang
            return lang
        except (ImportError, AttributeError):
            return None

    def _create_violation(
        self, file_path: str, node: Any, rule: Rule, desc: str | None = None
    ) -> ASTViolation:
        # Generate structural signature: hash(node_type + normalized_text)
        # We normalize text by stripping whitespace to make it drift-resistant
        text_content = node.text.decode("utf-8", errors="replace").strip()
        signature_base = f"{node.type}:{text_content}"
        signature = hashlib.md5(signature_base.encode("utf-8")).hexdigest()

        return ASTViolation(
            file=file_path,
            line=node.start_point[0] + 1,
            rule_id=rule.id,
            description=desc or rule.description,
            severity=rule.severity.value,
            signature=signature,
        )
