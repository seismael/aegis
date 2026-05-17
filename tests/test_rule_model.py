from aegis.core.models.governance import EnforcementMode, EngineType, Rule, Severity


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
