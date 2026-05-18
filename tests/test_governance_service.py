import os
from unittest.mock import MagicMock

from aegis.domain.evaluation.baseline import BaselineManager
from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.evaluation.service import EvaluationService
from aegis.domain.governance.service import GovernanceService
from aegis.domain.policy.models import Rule


class TestGovernanceService:
    """Tests for GovernanceService orchestration."""

    def _make_service(self, eval_svc=None, baseline_mgr=None):
        return GovernanceService(
            evaluation_service=eval_svc or MagicMock(spec=EvaluationService),
            baseline_manager=baseline_mgr or MagicMock(spec=BaselineManager),
        )

    def test_get_active_violations_filters_exempt(self):
        eval_mock = MagicMock(spec=EvaluationService)
        eval_mock.evaluate_workspace.return_value = [
            ArchitecturalViolation(file="a.py", line=1, rule_id="r1", description="x"),
            ArchitecturalViolation(file="b.py", line=2, rule_id="r2", description="y"),
        ]
        baseline_mock = MagicMock(spec=BaselineManager)

        # r1 is baselined (exempt), r2 is not
        def _is_exempt(violation, _rule):
            return violation.rule_id == "r1"

        baseline_mock.is_exempt.side_effect = _is_exempt

        svc = self._make_service(eval_mock, baseline_mock)
        rules = [
            Rule(id="r1", description="first"),
            Rule(id="r2", description="second"),
        ]
        active = svc.get_active_violations(rules, "/root")

        assert len(active) == 1
        assert active[0].rule_id == "r2"

    def test_get_active_violations_empty_workspace(self):
        eval_mock = MagicMock(spec=EvaluationService)
        eval_mock.evaluate_workspace.return_value = []
        baseline_mock = MagicMock(spec=BaselineManager)

        svc = self._make_service(eval_mock, baseline_mock)
        active = svc.get_active_violations([], "/root")
        assert active == []

    def test_capture_baseline_saves_and_returns_count(self):
        eval_mock = MagicMock(spec=EvaluationService)
        eval_mock.evaluate_workspace.return_value = [
            ArchitecturalViolation(file="a.py", line=1, rule_id="r1", description="x"),
            ArchitecturalViolation(file="b.py", line=2, rule_id="r1", description="y"),
        ]
        baseline_mock = MagicMock(spec=BaselineManager)

        svc = self._make_service(eval_mock, baseline_mock)
        count = svc.capture_baseline([Rule(id="r1", description="x")], "/root")

        assert count == 2
        baseline_mock.save_baseline.assert_called_once()

    def test_capture_baseline_zero_violations(self):
        eval_mock = MagicMock(spec=EvaluationService)
        eval_mock.evaluate_workspace.return_value = []
        baseline_mock = MagicMock(spec=BaselineManager)

        svc = self._make_service(eval_mock, baseline_mock)
        count = svc.capture_baseline([Rule(id="r1", description="x")], "/root")
        assert count == 0
        baseline_mock.save_baseline.assert_called_once_with([])

    def test_init_project_structure_creates_dirs_and_config(self, tmp_path):
        aegis_dir = GovernanceService.init_project_structure(str(tmp_path))
        assert aegis_dir == os.path.join(str(tmp_path), ".aegis")
        assert os.path.isdir(aegis_dir)
        assert os.path.isdir(os.path.join(aegis_dir, "rules"))
        config = os.path.join(aegis_dir, "config.yaml")
        assert os.path.exists(config)
        with open(config, encoding="utf-8") as f:
            assert "enforcement: warn" in f.read()

    def test_init_project_structure_idempotent(self, tmp_path):
        aegis_dir = GovernanceService.init_project_structure(str(tmp_path))
        aegis_dir2 = GovernanceService.init_project_structure(str(tmp_path))
        assert aegis_dir == aegis_dir2
        rules = os.listdir(os.path.join(aegis_dir, "rules"))
        # Rules only copied once
        assert (
            len(rules) == 3
        )  # architecture.yaml + security.yaml + cloud_isolation.yaml
