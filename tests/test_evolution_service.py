import json
import os

import pytest

from aegis.core.models.evolution import EvolutionDecision, EvolutionLog
from aegis.domain.evolution.service import EvolutionService


class TestEvolutionService:
    """Test suite for EvolutionService — architectural consensus ledger."""

    def _decision(self, rule_id="r1", action="suppress", rationale="ok"):
        return EvolutionDecision(
            rule_id=rule_id, action=action, rationale=rationale
        )

    def test_load_log_no_file(self, tmp_path):
        """No evolution log file → empty log."""
        svc = EvolutionService(str(tmp_path))
        log = svc.load_log()
        assert log.decisions == []

    def test_log_decision_persists(self, tmp_path):
        """log_decision writes a decision to disk."""
        svc = EvolutionService(str(tmp_path))
        d = self._decision()
        svc.log_decision(d)
        log = svc.load_log()
        assert len(log.decisions) == 1
        assert log.decisions[0].rule_id == "r1"

    def test_log_decision_skips_duplicate(self, tmp_path):
        """Same rule_id/action/rationale → skipped."""
        svc = EvolutionService(str(tmp_path))
        d = self._decision()
        svc.log_decision(d)
        svc.log_decision(d)
        log = svc.load_log()
        assert len(log.decisions) == 1

    def test_log_decision_allows_different_action(self, tmp_path):
        """Same rule_id but different action → appended."""
        svc = EvolutionService(str(tmp_path))
        svc.log_decision(self._decision(action="suppress"))
        svc.log_decision(self._decision(action="relax_rule"))
        log = svc.load_log()
        assert len(log.decisions) == 2

    def test_log_decision_allows_different_rationale(self, tmp_path):
        """Same rule_id/action but different rationale → appended."""
        svc = EvolutionService(str(tmp_path))
        svc.log_decision(self._decision(rationale="reason one"))
        svc.log_decision(self._decision(rationale="reason two"))
        log = svc.load_log()
        assert len(log.decisions) == 2

    def test_save_log_overwrites(self, tmp_path):
        """save_log replaces all entries."""
        svc = EvolutionService(str(tmp_path))
        svc.log_decision(self._decision())
        svc.save_log(EvolutionLog())
        log = svc.load_log()
        assert len(log.decisions) == 0

    def test_load_log_corrupted_json(self, tmp_path):
        """Corrupted JSON file returns empty log instead of crashing."""
        svc = EvolutionService(str(tmp_path))
        path = svc.path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("{invalid json")
        log = svc.load_log()
        assert log.decisions == []

    def test_load_log_empty_file(self, tmp_path):
        """Empty file returns empty log."""
        svc = EvolutionService(str(tmp_path))
        path = svc.path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        log = svc.load_log()
        assert log.decisions == []

    def test_load_log_invalid_type(self, tmp_path):
        """Valid JSON but wrong structure returns empty log."""
        svc = EvolutionService(str(tmp_path))
        path = svc.path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"not": "decisions"}, f)
        log = svc.load_log()
        assert log.decisions == []

    def test_multiple_decisions_preserved(self, tmp_path):
        """Multiple distinct decisions are all preserved."""
        svc = EvolutionService(str(tmp_path))
        decisions = [
            self._decision(rule_id="r1", action="suppress"),
            self._decision(rule_id="r2", action="relax_rule"),
            self._decision(rule_id="r3", action="refactor"),
        ]
        for d in decisions:
            svc.log_decision(d)
        log = svc.load_log()
        assert len(log.decisions) == 3
        assert {d.rule_id for d in log.decisions} == {"r1", "r2", "r3"}
