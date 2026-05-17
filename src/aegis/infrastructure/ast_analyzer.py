from typing import Any, List, Dict, Optional
import tree_sitter_python as tspython
from tree_sitter import Language, Parser, Query, QueryCursor
from aegis.domain.evaluation.ports import ASTAnalyzerInterface, ASTViolation
from aegis.core.models.governance import Rule

class TreeSitterAnalyzer(ASTAnalyzerInterface):
    """
    Polyglot AST analyzer implementation using Tree-sitter.
    Supports language-agnostic structural queries via S-expressions.
    """

    def __init__(self):
        self.languages = {
            "py": Language(tspython.language())
        }
        # Reuse parser across files for efficiency
        self._parser_cache: Dict[str, Parser] = {}
        # Simple AST cache: (file_path, content_hash) -> Tree
        self._tree_cache: Dict[str, Any] = {}

    def analyze_file(self, file_path: str, content: str, rules: List[Rule]) -> List[ASTViolation]:
        ext = file_path.split(".")[-1]
        
        # Filter rules by language
        relevant_rules = [r for r in rules if r.language == ext]
        if not relevant_rules:
            return []

        if ext not in self.languages:
            # In a real app, we might dynamically load the language library
            return []

        language = self.languages[ext]
        
        if ext not in self._parser_cache:
            self._parser_cache[ext] = Parser(language)
            
        parser = self._parser_cache[ext]
        
        # Cache check
        content_hash = hash(content)
        cache_key = f"{file_path}:{content_hash}"
        
        if cache_key in self._tree_cache:
            tree = self._tree_cache[cache_key]
        else:
            tree = parser.parse(bytes(content, "utf8"))
            self._tree_cache = {cache_key: tree} # Minimal cache to prevent memory explosion
        
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
                            violations.append(ASTViolation(
                                file=file_path,
                                line=node.start_point[0] + 1,
                                rule_id=rule.id,
                                description=rule.description,
                                severity=rule.severity.value
                            ))
                
                # Handle positive rules (candidates - check)
                elif rule.candidates_query and rule.check_query:
                    c_query = Query(language, rule.candidates_query)
                    c_cursor = QueryCursor(c_query)
                    candidates = c_cursor.captures(tree.root_node)
                    
                    compliance_query = Query(language, rule.check_query)
                    compliance_cursor = QueryCursor(compliance_query)
                    compliant = compliance_cursor.captures(tree.root_node)
                    
                    # Convert compliant captures to a set of start points for efficient lookup
                    compliant_points = set()
                    for nodes in compliant.values():
                        for node in nodes:
                            compliant_points.add(node.start_point)
                    
                    # Any candidate NOT in the compliant set is a violation
                    for nodes in candidates.values():
                        for node in nodes:
                            if node.start_point not in compliant_points:
                                violations.append(ASTViolation(
                                    file=file_path,
                                    line=node.start_point[0] + 1,
                                    rule_id=rule.id,
                                    description=f"Compliance check failed: {rule.description}",
                                    severity=rule.severity.value
                                ))
                                
            except Exception as e:
                logger.error("Query execution failed", rule=rule.id, error=str(e))
                continue
        
        return violations
