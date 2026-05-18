import os

from aegis.domain.evaluation.baseline import BaselineManager
from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.evaluation.service import EvaluationService
from aegis.domain.policy.models import Rule


class GovernanceService:
    """
    Application-level orchestration for project governance workflows.
    Consolidates logic shared between CLI and MCP Kernel to eliminate
    duplication of init, baseline capture, and active-violation filtering.
    """

    def __init__(
        self,
        evaluation_service: EvaluationService,
        baseline_manager: BaselineManager,
    ):
        self._evaluation_service = evaluation_service
        self._baseline_manager = baseline_manager

    def get_active_violations(
        self, rules: list[Rule], root_dir: str
    ) -> list[ArchitecturalViolation]:
        """Evaluate the workspace and filter out baselined (exempt) violations."""
        violations = self._evaluation_service.evaluate_workspace(root_dir, rules)
        rule_map = {r.id: r for r in rules}
        return [
            v
            for v in violations
            if not self._baseline_manager.is_exempt(v, rule_map.get(v.rule_id))
        ]

    def capture_baseline(self, rules: list[Rule], root_dir: str) -> int:
        """Evaluate and persist current violations as the technical debt baseline."""
        violations = self._evaluation_service.evaluate_workspace(root_dir, rules)
        self._baseline_manager.save_baseline(violations)
        return len(violations)

    @staticmethod
    def init_project_structure(root_dir: str) -> str | None:
        """
        Bootstrap .aegis/ governance directory with config and default rule packs.
        Returns the .aegis path on success, or None if it already existed.
        """
        aegis_dir = os.path.join(root_dir, ".aegis")
        if not os.path.exists(aegis_dir):
            os.makedirs(aegis_dir)

        config_path = os.path.join(aegis_dir, "config.yaml")
        if not os.path.exists(config_path):
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(
                    "enforcement: warn\n"
                    "# Optional: override default evaluation phases per category\n"
                    "# phase_defaults:\n"
                    "#   style: [pre-commit]\n"
                    "#   security: [ci, nightly, on-demand]\n"
                )

        rules_dir = os.path.join(aegis_dir, "rules")
        if not os.path.exists(rules_dir):
            os.makedirs(rules_dir)
            from aegis.domain.policy.pack_manager import RulePackManager

            RulePackManager(rules_dir).install_defaults()

        return aegis_dir
