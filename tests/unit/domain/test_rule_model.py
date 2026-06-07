from aegis.domain.policy.models import (
    CategoryPhaseMapping,
    EnforcementMode,
    EngineType,
    EvaluationPhase,
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


class TestEvaluationPhase:
    """Tests for the EvaluationPhase enum."""

    def test_values(self):
        assert EvaluationPhase.PRE_COMMIT == "pre-commit"
        assert EvaluationPhase.PRE_PUSH == "pre-push"
        assert EvaluationPhase.CI == "ci"
        assert EvaluationPhase.NIGHTLY == "nightly"
        assert EvaluationPhase.ON_DEMAND == "on-demand"

    def test_all_phases_covered(self):
        phases = list(EvaluationPhase)
        assert len(phases) == 5


class TestExpandedRuleCategory:
    """Tests for the expanded RuleCategory enum (4→13 values)."""

    def test_existing_values_preserved(self):
        assert RuleCategory.ARCHITECTURE == "architecture"
        assert RuleCategory.SECURITY == "security"
        assert RuleCategory.TESTING == "testing"
        assert RuleCategory.STYLE == "style"

    def test_new_values(self):
        assert RuleCategory.STRUCTURE == "structure"
        assert RuleCategory.DESIGN == "design"
        assert RuleCategory.BEST_PRACTICES == "best-practices"
        assert RuleCategory.TOOLS == "tools"
        assert RuleCategory.PERFORMANCE == "performance"
        assert RuleCategory.DOCUMENTATION == "documentation"
        assert RuleCategory.DEPENDENCIES == "dependencies"
        assert RuleCategory.INFRASTRUCTURE == "infrastructure"
        assert RuleCategory.GENERAL == "general"

    def test_total_count(self):
        assert len(list(RuleCategory)) == 18

    def test_yaml_string_deserialization(self):
        rule = Rule.model_validate(
            {"id": "r1", "description": "d", "category": "structure"}
        )
        assert rule.category == RuleCategory.STRUCTURE

        rule2 = Rule.model_validate(
            {"id": "r2", "description": "d", "category": "design"}
        )
        assert rule2.category == RuleCategory.DESIGN

    def test_serialization_roundtrip_new_categories(self):
        for cat in RuleCategory:
            rule = Rule(id="r1", description="d", category=cat)
            data = rule.model_dump()
            restored = Rule(**data)
            assert restored.category == cat


class TestRulePhases:
    """Tests for the Rule.phases field."""

    def test_default_is_none(self):
        rule = Rule(id="test", description="desc")
        assert rule.phases is None

    def test_explicit_phases_list(self):
        rule = Rule(
            id="test",
            description="desc",
            phases=[EvaluationPhase.PRE_COMMIT, EvaluationPhase.CI],
        )
        assert rule.phases == [EvaluationPhase.PRE_COMMIT, EvaluationPhase.CI]

    def test_single_phase(self):
        rule = Rule(
            id="test",
            description="desc",
            phases=[EvaluationPhase.NIGHTLY],
        )
        assert rule.phases == [EvaluationPhase.NIGHTLY]

    def test_serialization_roundtrip(self):
        rule = Rule(
            id="r1",
            description="desc",
            phases=[EvaluationPhase.CI, EvaluationPhase.NIGHTLY],
        )
        data = rule.model_dump()
        restored = Rule(**data)
        assert restored.phases == [EvaluationPhase.CI, EvaluationPhase.NIGHTLY]

    def test_yaml_string_deserialization(self):
        rule = Rule.model_validate(
            {"id": "r1", "description": "d", "phases": ["ci", "nightly"]}
        )
        assert rule.phases == [EvaluationPhase.CI, EvaluationPhase.NIGHTLY]

    def test_phases_omitted_in_yaml(self):
        rule = Rule.model_validate({"id": "r1", "description": "d"})
        assert rule.phases is None


class TestCategoryPhaseMapping:
    """Tests for the CategoryPhaseMapping model."""

    def test_all_categories_mapped(self):
        mapping = CategoryPhaseMapping()
        mapped = set(mapping.category_defaults.keys())
        expected = set(RuleCategory)
        assert mapped == expected, f"Missing: {expected - mapped}"

    def test_phase_values_are_valid(self):
        mapping = CategoryPhaseMapping()
        for cat, phases in mapping.category_defaults.items():
            for phase in phases:
                assert isinstance(phase, EvaluationPhase), f"{cat}: {phase}"

    def test_default_can_be_overridden(self):
        mapping = CategoryPhaseMapping(
            category_defaults={
                RuleCategory.SECURITY: [EvaluationPhase.PRE_COMMIT],
            }
        )
        assert mapping.category_defaults[RuleCategory.SECURITY] == [
            EvaluationPhase.PRE_COMMIT
        ]

    def test_serialization_roundtrip(self):
        mapping = CategoryPhaseMapping()
        data = mapping.model_dump()
        restored = CategoryPhaseMapping(**data)
        assert restored.category_defaults == mapping.category_defaults
