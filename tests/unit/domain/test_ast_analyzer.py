from aegis.domain.evaluation.analyzers.ast import TreeSitterAnalyzer
from aegis.domain.policy.models import Rule, Severity


class TestTreeSitterAnalyzer:
    """
    Test suite for the Polyglot TreeSitterAnalyzer.
    """

    # --- Core language detection ---

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
        assert violations[0].signature is not None

    def test_typescript_analysis(self):
        analyzer = TreeSitterAnalyzer()
        rules = [
            Rule(
                id="no-console-log",
                query='(call_expression function: (member_expression object: (identifier) @obj property: (property_identifier) @prop) (#eq? @obj "console") (#eq? @prop "log")) @violation',  # noqa: E501
                description="No console.log allowed.",
                severity=Severity.MEDIUM,
                language="ts",
            )
        ]
        content = "console.log('test');"
        violations = analyzer.analyze_file("test.ts", content, rules)
        assert len(violations) >= 1

    # --- Positive rules ---

    def test_positive_rule_enforcement(self):
        analyzer = TreeSitterAnalyzer()
        rules = [
            Rule(
                id="require-docstring",
                candidates_query="(class_definition) @class",
                check_query=(
                    "(class_definition body:"
                    " (block (expression_statement (string)))) @class"
                ),
                description="Classes must have docstrings.",
                severity=Severity.LOW,
                language="py",
            )
        ]
        content_bad = "class NoDoc: pass"
        violations = analyzer.analyze_file("test.py", content_bad, rules)
        assert len(violations) == 1

        content_good = 'class HasDoc:\n    """Docstring."""\n    pass'
        violations = analyzer.analyze_file("test.py", content_good, rules)
        assert len(violations) == 0

    def test_positive_rule_multiple_candidates(self):
        """With multiple candidates, only non-compliant ones are flagged."""
        analyzer = TreeSitterAnalyzer()
        rules = [
            Rule(
                id="require-docstring",
                candidates_query="(class_definition) @class",
                check_query=(
                    "(class_definition body:"
                    " (block (expression_statement (string)))) @class"
                ),
                description="Classes must have docstrings.",
                severity=Severity.LOW,
                language="py",
            )
        ]
        content = (
            'class HasDoc:\n    """Has doc."""\n    pass\n\n'
            "class NoDoc:\n    pass\n\n"
            'class AlsoDoc:\n    """Also doc."""\n    pass\n'
        )
        violations = analyzer.analyze_file("test.py", content, rules)
        assert len(violations) == 1
        assert violations[0].line == 5  # NoDoc is line 5

    def test_positive_rule_no_candidates(self):
        """No candidates means no violations."""
        analyzer = TreeSitterAnalyzer()
        rules = [
            Rule(
                id="require-docstring",
                candidates_query="(class_definition) @class",
                check_query=(
                    "(class_definition body:"
                    " (block (expression_statement (string)))) @class"
                ),
                description="Classes must have docstrings.",
                language="py",
            )
        ]
        violations = analyzer.analyze_file("test.py", "x = 1", rules)
        assert violations == []

    def test_positive_rule_invalid_candidates_query(self):
        """Invalid candidates_query does not crash."""
        analyzer = TreeSitterAnalyzer()
        rules = [
            Rule(
                id="bad-candidates",
                candidates_query="((( this is not valid",
                check_query="(class_definition) @cls",
                description="test",
                language="py",
            )
        ]
        violations = analyzer.analyze_file("test.py", "class Foo: pass", rules)
        assert violations == []

    def test_positive_rule_invalid_check_query(self):
        """Invalid check_query does not crash."""
        analyzer = TreeSitterAnalyzer()
        rules = [
            Rule(
                id="bad-check",
                candidates_query="(class_definition) @cls",
                check_query="((( this is not valid",
                description="test",
                language="py",
            )
        ]
        violations = analyzer.analyze_file("test.py", "class Foo: pass", rules)
        assert violations == []

    def test_positive_rule_query_priority(self):
        """Standard query takes priority over candidates_query when both set."""
        analyzer = TreeSitterAnalyzer()
        rules = [
            Rule(
                id="mixed",
                query="(function_definition) @fn",
                candidates_query="(class_definition) @cls",
                check_query=(
                    "(class_definition body:"
                    " (block (expression_statement (string)))) @cls"
                ),
                description="test",
                language="py",
            )
        ]
        # query is checked first in analyze_file, so standard query path wins
        violations = analyzer.analyze_file(
            "test.py", "class NoDoc:\n    pass\n\ndef f(): pass\n", rules
        )
        assert len(violations) == 1
        assert violations[0].line == 4  # function at line 4, not class at line 1

    # --- Signature stability ---

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

        content_shifted = "\n\n# New Comment\ndef f(): pass"
        v2 = analyzer.analyze_file("test.py", content_shifted, [rule])[0]
        assert v1.signature == v2.signature
        assert v1.line != v2.line

    # --- Extension/language edge cases ---

    def test_unsupported_extension_returns_empty(self):
        """Analyzer returns empty for unsupported file extensions."""
        analyzer = TreeSitterAnalyzer()
        rule = Rule(
            id="r1",
            query="(function_definition) @fn",
            description="test",
            language="py",
        )
        result = analyzer.analyze_file("file.xyz", "content", [rule])
        assert result == []

    def test_no_rules_matching_language(self):
        """No violations when rules target different language."""
        analyzer = TreeSitterAnalyzer()
        rule = Rule(
            id="r1",
            query="(function_definition) @fn",
            description="test",
            language="rs",
        )
        result = analyzer.analyze_file("file.py", "x = 1", [rule])
        assert result == []

    def test_no_rules_at_all(self):
        """Empty rules list returns empty."""
        analyzer = TreeSitterAnalyzer()
        result = analyzer.analyze_file("file.py", "x = 1", [])
        assert result == []

    def test_empty_file(self):
        """Empty content produces no violations."""
        analyzer = TreeSitterAnalyzer()
        rule = Rule(
            id="r1",
            query="(function_definition) @fn",
            description="test",
            language="py",
        )
        result = analyzer.analyze_file("empty.py", "", [rule])
        assert result == []

    # --- Query error resilience ---

    def test_invalid_query_does_not_crash(self):
        """Syntax error in query string is caught, no crash."""
        analyzer = TreeSitterAnalyzer()
        rule = Rule(
            id="r1",
            query="(this is not valid syntax",
            description="test",
            language="py",
        )
        result = analyzer.analyze_file("test.py", "x = 1", [rule])
        assert result == []

    def test_invalid_query_does_not_block_other_rules(self):
        """One broken query doesn't prevent other rules from matching."""
        analyzer = TreeSitterAnalyzer()
        rules = [
            Rule(
                id="bad", query="(not valid syntax", description="test", language="py"
            ),
            Rule(
                id="good",
                query="(function_definition) @fn",
                description="test",
                language="py",
            ),
        ]
        result = analyzer.analyze_file("test.py", "def foo():\n    pass\n", rules)
        assert len(result) == 1
        assert result[0].rule_id == "good"

    # --- Multiple nodes / multiple rules ---

    def test_multiple_matches(self):
        """Multiple matching nodes in a single file."""
        analyzer = TreeSitterAnalyzer()
        rule = Rule(
            id="r1",
            query="(function_definition) @fn",
            description="test",
            language="py",
        )
        result = analyzer.analyze_file(
            "test.py",
            "def a():\n    pass\n\ndef b():\n    pass\n",
            [rule],
        )
        assert len(result) == 2

    def test_multiple_rules_on_same_file(self):
        """Multiple rules each produce their own violations."""
        analyzer = TreeSitterAnalyzer()
        rules = [
            Rule(
                id="no-func",
                query="(function_definition) @fn",
                description="test",
                language="py",
            ),
            Rule(
                id="no-class",
                query="(class_definition) @cls",
                description="test",
                language="py",
            ),
        ]
        result = analyzer.analyze_file(
            "test.py",
            "class Foo:\n    pass\n\ndef bar():\n    pass\n",
            rules,
        )
        assert len(result) == 2
        assert {v.rule_id for v in result} == {"no-func", "no-class"}

    # --- Unicode ---

    def test_unicode_content(self):
        """File with unicode characters is handled without encoding errors."""
        analyzer = TreeSitterAnalyzer()
        rule = Rule(
            id="r1",
            query="(function_definition) @fn",
            description="test",
            language="py",
        )
        result = analyzer.analyze_file(
            "test.py",
            "# -*- coding: utf-8 -*-\ndef fete():\n    pass\n",
            [rule],
        )
        assert len(result) == 1
        assert result[0].line == 2

    # --- JavaScript ---

    def test_javascript_analysis(self):
        """JavaScript function declarations are detected."""
        analyzer = TreeSitterAnalyzer()
        rule = Rule(
            id="no-func",
            query="(function_declaration) @fn",
            description="test",
            language="js",
        )
        result = analyzer.analyze_file(
            "app.js", "function hello() { return 1; }\n", [rule]
        )
        assert len(result) == 1
        assert result[0].line == 1
