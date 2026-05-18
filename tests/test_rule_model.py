from aegis.domain.policy.models import (
    EnforcementMode,
    EngineType,
    Rule,
    RuleCategory,
    Severity,
)


class TestRuleModel:
    """
    Test suite for the Rule model with engine_type and rationale fields.
    """

    def test_defaults_to_tree_sitter(self):
        rule = Rule(id="test", description="desc")
        assert rule.engine_type == EngineType.TREE_SITTER

    def test_engine_type_graph(self):
        rule = Rule(id="test", description="desc", engine_type=EngineType.GRAPH)
        assert rule.engine_type == EngineType.GRAPH

    def test_engine_type_regex(self):
        rule = Rule(id="test", description="desc", engine_type=EngineType.REGEX)
        assert rule.engine_type == EngineType.REGEX

    def test_rationale_field(self):
        rule = Rule(id="test", description="desc", rationale="Because.")
        assert rule.rationale == "Because."

    def test_rationale_omitted(self):
        rule = Rule(id="test", description="desc")
        assert rule.rationale is None

    def test_serialization_roundtrip(self):
        rule = Rule(
            id="r1",
            description="desc",
            engine_type=EngineType.GRAPH,
            rationale="Keep it clean.",
            severity=Severity.CRITICAL,
            mode=EnforcementMode.BLOCK,
        )
        data = rule.model_dump()
        restored = Rule(**data)
        assert restored.engine_type == EngineType.GRAPH
        assert restored.rationale == "Keep it clean."
        assert restored.severity == Severity.CRITICAL
        assert restored.mode == EnforcementMode.BLOCK

    def test_engine_type_no_conflict_with_existing_fields(self):
        rule = Rule(
            id="r",
            description="d",
            query="(module) @m",
            language="py",
            candidates_query="(class) @c",
            check_query="(docstring) @d",
            applies_to=["src/**/*.py"],
            excludes=["tests/"],
            owner="team-a",
        )
        assert rule.engine_type == EngineType.TREE_SITTER
        assert rule.query == "(module) @m"
        assert rule.language == "py"

    def test_category_defaults_to_architecture(self):
        rule = Rule(id="test", description="desc")
        assert rule.category == RuleCategory.ARCHITECTURE

    def test_category_security(self):
        rule = Rule(id="test", description="desc", category=RuleCategory.SECURITY)
        assert rule.category == RuleCategory.SECURITY

    def test_category_serialization_roundtrip(self):
        rule = Rule(id="r1", description="d", category=RuleCategory.SECURITY)
        data = rule.model_dump()
        restored = Rule(**data)
        assert restored.category == RuleCategory.SECURITY

    def test_category_from_yaml_string(self):
        rule = Rule.model_validate(
            {"id": "r1", "description": "d", "category": "security"}
        )
        assert rule.category == RuleCategory.SECURITY
