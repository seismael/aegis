from aegis.domain.evaluation.analyzers.semantic import SemanticAnalyzer
from aegis.domain.policy.models import EngineType, Rule, Severity


def test_semantic_analyzer_rubric_generation():
    """
    Verifies that the SemanticAnalyzer correctly builds a grading rubric
    for high-level architectural intents. This is the 'most significant' test
    as it powers the agent-native self-correction loop.
    """
    analyzer = SemanticAnalyzer()
    rules = [
        Rule(
            id="arch-no-global-state",
            description="Global state is forbidden in the microkernel.",
            engine_type=EngineType.SEMANTIC,
            severity=Severity.CRITICAL,
        ),
        Rule(
            id="sec-no-pii-logging",
            description="PII must not be logged.",
            engine_type=EngineType.SEMANTIC,
            severity=Severity.HIGH,
        ),
    ]

    rubric = analyzer.build_rubric("src/kernel/server.py", rules)

    assert "### 🧩 Semantic Grading Rubric for `src/kernel/server.py`" in rubric
    assert "**arch-no-global-state**" in rubric
    assert "Global state is forbidden in the microkernel." in rubric
    assert "`CRITICAL`" in rubric
    assert "**sec-no-pii-logging**" in rubric
    assert "PII must not be logged." in rubric
    assert "`HIGH`" in rubric
    assert "VIOLATION: <rule_id> - <line_number>" in rubric


def test_semantic_analyzer_heuristic_triggers():
    """
    Verifies the fallback heuristic for semantic rules in CI environments.
    """
    analyzer = SemanticAnalyzer()
    rules = [
        Rule(
            id="sec-no-leak",
            description="Do not leak secrets.",
            engine_type=EngineType.SEMANTIC,
            metadata={"sim_triggers": ["password", "secret_key"]},
        )
    ]

    # Case: Violation triggered by heuristic
    content = "config = {'password': '123'}"
    violations = analyzer.analyze_semantic("config.py", content, rules)
    assert len(violations) == 1
    assert violations[0].rule_id == "sec-no-leak"
    assert "Detected triggers: password" in violations[0].description

    # Case: No violation
    content = "print('hello world')"
    violations = analyzer.analyze_semantic("hello.py", content, rules)
    assert len(violations) == 0
