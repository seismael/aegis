"""Tests for phase-based rule filtering (EvaluationService.filter_rules_by_phase)."""

from aegis.domain.evaluation.service import EvaluationService
from aegis.domain.policy.models import (
    CategoryPhaseMapping,
    EnforcementMode,
    EvaluationPhase,
    Rule,
    RuleCategory,
    Severity,
)


class TestFilterRulesByPhase:
    """Tests for EvaluationService.filter_rules_by_phase()."""

    def _make_rule(self, rid: str, category: RuleCategory, phases=None) -> Rule:
        return Rule(
            id=rid,
            description=rid,
            category=category,
            phases=phases,
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
        )

    def test_none_phase_returns_all(self):
        rules = [
            self._make_rule("r1", RuleCategory.STYLE, [EvaluationPhase.PRE_COMMIT]),
            self._make_rule("r2", RuleCategory.SECURITY, [EvaluationPhase.CI]),
        ]
        result = EvaluationService.filter_rules_by_phase(rules)
        assert len(result) == 2

    def test_phase_filter_matches_explicit(self):
        rules = [
            self._make_rule("r1", RuleCategory.STYLE, [EvaluationPhase.PRE_COMMIT]),
            self._make_rule("r2", RuleCategory.SECURITY, [EvaluationPhase.CI]),
        ]
        result = EvaluationService.filter_rules_by_phase(
            rules, phase=EvaluationPhase.PRE_COMMIT
        )
        assert len(result) == 1
        assert result[0].id == "r1"

    def test_phase_filter_uses_category_default(self):
        """Rule without explicit phases inherits from category mapping."""
        rules = [
            self._make_rule("r1", RuleCategory.STYLE),  # no explicit phases
        ]
        # STYLE defaults to PRE_COMMIT
        result = EvaluationService.filter_rules_by_phase(
            rules, phase=EvaluationPhase.PRE_COMMIT
        )
        assert len(result) == 1
        assert result[0].id == "r1"

    def test_phase_filter_unmatched_category_default(self):
        """Rule without phases whose category doesn't map to the phase is excluded."""
        rules = [
            self._make_rule("r1", RuleCategory.GENERAL),  # GENERAL → ON_DEMAND
        ]
        result = EvaluationService.filter_rules_by_phase(
            rules, phase=EvaluationPhase.PRE_COMMIT
        )
        assert len(result) == 0

    def test_category_filter(self):
        rules = [
            self._make_rule("r1", RuleCategory.SECURITY),
            self._make_rule("r2", RuleCategory.STYLE),
        ]
        result = EvaluationService.filter_rules_by_phase(
            rules, category=RuleCategory.SECURITY
        )
        assert len(result) == 1
        assert result[0].id == "r1"

    def test_combined_phase_and_category(self):
        rules = [
            self._make_rule("r1", RuleCategory.STYLE, [EvaluationPhase.PRE_COMMIT]),
            self._make_rule("r2", RuleCategory.STYLE, [EvaluationPhase.CI]),
            self._make_rule("r3", RuleCategory.SECURITY, [EvaluationPhase.CI]),
        ]
        result = EvaluationService.filter_rules_by_phase(
            rules, phase=EvaluationPhase.CI, category=RuleCategory.STYLE
        )
        assert len(result) == 1
        assert result[0].id == "r2"

    def test_custom_mapping_overrides_default(self):
        rules = [
            self._make_rule("r1", RuleCategory.SECURITY),  # no explicit phases
        ]
        custom_mapping = CategoryPhaseMapping(
            category_defaults={
                RuleCategory.SECURITY: [EvaluationPhase.PRE_COMMIT],
            }
        )
        result = EvaluationService.filter_rules_by_phase(
            rules, phase=EvaluationPhase.PRE_COMMIT, phase_mapping=custom_mapping
        )
        assert len(result) == 1

    def test_explicit_phases_override_category(self):
        """Rule with explicit phases uses them, not category defaults."""
        rules = [
            self._make_rule("r1", RuleCategory.STYLE, [EvaluationPhase.NIGHTLY]),
        ]
        # STYLE defaults to PRE_COMMIT, but explicit phases say NIGHTLY
        result_pre = EvaluationService.filter_rules_by_phase(
            rules, phase=EvaluationPhase.PRE_COMMIT
        )
        result_nightly = EvaluationService.filter_rules_by_phase(
            rules, phase=EvaluationPhase.NIGHTLY
        )
        assert len(result_pre) == 0
        assert len(result_nightly) == 1

    def test_empty_phases_list_excludes_from_all_phases(self):
        """A rule with phases=[] should never match any phase filter."""
        rules = [
            self._make_rule("r1", RuleCategory.STYLE, phases=[]),
        ]
        for phase in EvaluationPhase:
            result = EvaluationService.filter_rules_by_phase(rules, phase=phase)
            assert len(result) == 0, f"Should not match {phase}"
