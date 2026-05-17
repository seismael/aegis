from aegis.core.models.governance import Rule, Severity
from aegis.infrastructure.ast_analyzer import TreeSitterAnalyzer


class TestTreeSitterAnalyzer:
    """
    Test suite for the Polyglot TreeSitterAnalyzer.
    """

    def test_python_analysis(self):
        analyzer = TreeSitterAnalyzer()
        rules = [
            Rule(
                id="no-loose-functions",
                query="(module (function_definition) @violation)",
                description="No loose functions.",
                severity=Severity.HIGH,
                language="py",
            )
        ]
        content = "def loose(): pass"
        violations = analyzer.analyze_file("test.py", content, rules)
        assert len(violations) == 1
        assert violations[0].rule_id == "no-loose-functions"
        # Verify signature is present
        assert violations[0].signature is not None

    def test_typescript_analysis(self):
        analyzer = TreeSitterAnalyzer()
        # Ensure we have tree-sitter-typescript installed for this to work
        rules = [
            Rule(
                id="no-console-log",
                query='(call_expression function: (member_expression object: (identifier) @obj property: (property_identifier) @prop) (#eq? @obj "console") (#eq? @prop "log")) @violation',
                description="No console.log allowed.",
                severity=Severity.MEDIUM,
                language="ts",
            )
        ]
        content = "console.log('test');"
        violations = analyzer.analyze_file("test.ts", content, rules)
        # Note: If tree-sitter-typescript isn't perfectly wired, this might be 0
        # But we added it in the 'uv add' step.
        assert len(violations) >= 1

    def test_positive_rule_enforcement(self):
        analyzer = TreeSitterAnalyzer()
        rules = [
            Rule(
                id="require-docstring",
                candidates_query="(class_definition) @class",
                check_query="(class_definition body: (block (expression_statement (string)))) @class",
                description="Classes must have docstrings.",
                severity=Severity.LOW,
                language="py",
            )
        ]

        # 1. Non-compliant class
        content_bad = "class NoDoc: pass"
        violations = analyzer.analyze_file("test.py", content_bad, rules)
        assert len(violations) == 1

        # 2. Compliant class
        content_good = 'class HasDoc:\n    """Docstring."""\n    pass'
        violations = analyzer.analyze_file("test.py", content_good, rules)
        assert len(violations) == 0

    def test_signature_stability(self):
        analyzer = TreeSitterAnalyzer()
        rule = Rule(
            id="r",
            query="(module (function_definition) @v)",
            language="py",
            description="desc",
        )
        content = "def f(): pass"

        v1 = analyzer.analyze_file("test.py", content, [rule])[0]

        # Add comments/whitespace change elsewhere
        content_shifted = "\n\n# New Comment\ndef f(): pass"
        v2 = analyzer.analyze_file("test.py", content_shifted, [rule])[0]

        # Signatures must match even if line changed
        assert v1.signature == v2.signature
        assert v1.line != v2.line
