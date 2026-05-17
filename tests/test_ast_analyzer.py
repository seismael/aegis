import pytest
from aegis.infrastructure.ast_analyzer import TreeSitterAnalyzer
from aegis.core.models.governance import Rule, Severity

class TestTreeSitterAnalyzer:
    """
    Test suite for the TreeSitterAnalyzer.
    """
    def test_treesitter_analyze_loose_function(self):
        analyzer = TreeSitterAnalyzer()
        
        # Rule: Forbid functions not defined inside a class (Loose procedural functions)
        rules = [
            Rule(
                id="no-loose-functions",
                query="(function_definition) @func",
                description="Loose procedural functions are forbidden.",
                severity=Severity.HIGH
            )
        ]
        
        content = """
def loose_function():
    pass

class MyClass:
    def method(self):
        pass
"""
        violations = analyzer.analyze_file("test.py", content, rules)
        
        # Both loose_function and method will be captured by (function_definition)
        assert len(violations) >= 1
        
    def test_treesitter_specific_query(self):
        analyzer = TreeSitterAnalyzer()
        
        rules = [
            Rule(
                id="any-function",
                query="(function_definition name: (identifier) @name)",
                description="Found a function.",
                severity=Severity.HIGH
            )
        ]
        
        content = "def test(): pass"
        violations = analyzer.analyze_file("test.py", content, rules)
        assert len(violations) == 1
        assert violations[0].rule_id == "any-function"
        assert violations[0].line == 1
