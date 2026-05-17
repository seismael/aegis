from aegis.domain.evaluation.baseline import BaselineManager
from aegis.domain.evaluation.ports import ArchitecturalViolation


class TestBaselineManager:
    """Test suite for BaselineManager — architectural debt ledger."""

    def _violation(self, file, line, rule_id, signature=None):
        return ArchitecturalViolation(
            file=file, line=line, rule_id=rule_id, description="test", signature=signature
        )

    def test_is_exempt_no_baseline_file(self, tmp_path):
        """No baseline file → no violation is exempt."""
        bm = BaselineManager(str(tmp_path))
        v = self._violation("src/main.py", 10, "r1")
        assert not bm.is_exempt(v)

    def test_is_exempt_signature_match(self, tmp_path):
        """Signature match returns exempt."""
        bm = BaselineManager(str(tmp_path))
        v = self._violation("src/main.py", 10, "r1", signature="abc123")
        bm.add_to_baseline(v)
        assert bm.is_exempt(v)

    def test_is_exempt_file_line_rule_fallback(self, tmp_path):
        """File/line/rule fallback match when no signature."""
        bm = BaselineManager(str(tmp_path))
        v = self._violation("src/main.py", 10, "r1")
        bm.add_to_baseline(v)
        assert bm.is_exempt(v)

    def test_is_exempt_no_match(self, tmp_path):
        """Different rule_id → not exempt."""
        bm = BaselineManager(str(tmp_path))
        bm.add_to_baseline(self._violation("src/main.py", 10, "r1"))
        v2 = self._violation("src/main.py", 10, "r2")
        assert not bm.is_exempt(v2)

    def test_is_exempt_different_file(self, tmp_path):
        """Different file → not exempt."""
        bm = BaselineManager(str(tmp_path))
        bm.add_to_baseline(self._violation("src/main.py", 10, "r1"))
        v2 = self._violation("src/other.py", 10, "r1")
        assert not bm.is_exempt(v2)

    def test_is_exempt_different_line(self, tmp_path):
        """Different line → not exempt when no signature (relies on fallback)."""
        bm = BaselineManager(str(tmp_path))
        bm.add_to_baseline(self._violation("src/main.py", 10, "r1"))
        v2 = self._violation("src/main.py", 20, "r1")
        assert not bm.is_exempt(v2)

    def test_add_to_baseline_persists(self, tmp_path):
        """add_to_baseline persists entry to disk."""
        bm = BaselineManager(str(tmp_path))
        v = self._violation("src/main.py", 10, "r1")
        bm.add_to_baseline(v)
        raw = bm.load_baseline_raw()
        assert len(raw) == 1
        assert raw[0]["file"] == "src/main.py"
        assert raw[0]["rule_id"] == "r1"

    def test_add_to_baseline_skips_duplicate(self, tmp_path):
        """Adding the same violation twice stores only one entry."""
        bm = BaselineManager(str(tmp_path))
        v = self._violation("src/main.py", 10, "r1")
        bm.add_to_baseline(v)
        bm.add_to_baseline(v)
        raw = bm.load_baseline_raw()
        assert len(raw) == 1

    def test_save_baseline_overwrites(self, tmp_path):
        """save_baseline replaces all entries."""
        bm = BaselineManager(str(tmp_path))
        bm.add_to_baseline(self._violation("src/main.py", 10, "r1"))
        bm.save_baseline([])
        raw = bm.load_baseline_raw()
        assert len(raw) == 0

    def test_save_baseline_multiple(self, tmp_path):
        """save_baseline with multiple violations."""
        bm = BaselineManager(str(tmp_path))
        violations = [
            self._violation("a.py", 1, "r1"),
            self._violation("b.py", 2, "r2"),
        ]
        bm.save_baseline(violations)
        raw = bm.load_baseline_raw()
        assert len(raw) == 2

    def test_prune_stale_removes_entries(self, tmp_path):
        """prune_stale removes entries for rules that no longer exist."""
        bm = BaselineManager(str(tmp_path))
        bm.add_to_baseline(self._violation("a.py", 1, "r1"))
        bm.add_to_baseline(self._violation("b.py", 2, "r2_stale"))
        count = bm.prune_stale({"r1"})
        assert count == 1
        raw = bm.load_baseline_raw()
        assert len(raw) == 1
        assert raw[0]["rule_id"] == "r1"

    def test_prune_stale_noop_when_all_active(self, tmp_path):
        """prune_stale returns 0 when all rules are still active."""
        bm = BaselineManager(str(tmp_path))
        bm.add_to_baseline(self._violation("a.py", 1, "r1"))
        count = bm.prune_stale({"r1"})
        assert count == 0

    def test_prune_stale_no_file(self, tmp_path):
        """prune_stale returns 0 when no baseline file exists."""
        bm = BaselineManager(str(tmp_path))
        count = bm.prune_stale({"r1"})
        assert count == 0

    def test_match_malformed_entry_missing_keys(self, tmp_path):
        """_match handles malformed baseline entries without KeyError."""
        bm = BaselineManager(str(tmp_path))
        v = self._violation("src/main.py", 10, "r1")

        # Manually inject a malformed entry via raw baseline
        bm.save_baseline([v])
        raw = bm.load_baseline_raw()
        assert len(raw) == 1
        assert bm.is_exempt(v)

    def test_match_empty_signature_in_baseline(self, tmp_path):
        """Empty string signature in baseline does not crash."""
        bm = BaselineManager(str(tmp_path))
        bm.add_to_baseline(self._violation("src/main.py", 10, "r1", signature=""))
        v = self._violation("src/main.py", 10, "r1", signature="abc")
        # Signature match fails (baseline sig is empty), falls to file/line/rule
        assert bm.is_exempt(v)

    def test_exempt_updates_after_new_baseline(self, tmp_path):
        """Previously non-exempt violation becomes exempt after save_baseline."""
        bm = BaselineManager(str(tmp_path))
        v = self._violation("src/main.py", 10, "r1")
        assert not bm.is_exempt(v)
        bm.save_baseline([v])
        assert bm.is_exempt(v)
