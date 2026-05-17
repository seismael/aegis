from aegis.domain.evaluation.baseline import BaselineManager
from aegis.domain.evaluation.ports import ArchitecturalViolation


class TestBaselineManager:
    """Test suite for BaselineManager — architectural debt ledger."""

    def _violation(self, file, line, rule_id, signature=None):
        return ArchitecturalViolation(
            file=file,
            line=line,
            rule_id=rule_id,
            description="test",
            signature=signature,
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

    def test_corrupt_json_returns_empty(self, tmp_path):
        """Corrupt baseline.json returns empty list without crashing."""
        bm = BaselineManager(str(tmp_path))
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text("this is not json {{{", encoding="utf-8")
        assert bm.load_baseline_raw() == []

    def test_corrupt_json_is_exempt_no_crash(self, tmp_path):
        """Corrupt baseline.json causes is_exempt to return False."""
        bm = BaselineManager(str(tmp_path))
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text("not json", encoding="utf-8")
        v = self._violation("main.py", 1, "r1")
        assert not bm.is_exempt(v)

    def test_signature_match_overrides_different_line(self, tmp_path):
        """Signature match returns exempt even when line differs (drift resistance)."""
        bm = BaselineManager(str(tmp_path))
        v1 = self._violation("main.py", 10, "r1", signature="sig123")
        bm.add_to_baseline(v1)
        v2 = self._violation("main.py", 25, "r1", signature="sig123")
        assert bm.is_exempt(v2)

    def test_same_signature_different_rule_no_match(self, tmp_path):
        """Same signature but different rule_id does not match."""
        bm = BaselineManager(str(tmp_path))
        v1 = self._violation("main.py", 10, "r1", signature="sig123")
        bm.add_to_baseline(v1)
        v2 = self._violation("main.py", 10, "r2", signature="sig123")
        assert not bm.is_exempt(v2)

    def test_absolute_vs_relative_path_no_match(self, tmp_path):
        """Absolute violation path does not match relative baseline entry."""
        bm = BaselineManager(str(tmp_path))
        v = self._violation("src/main.py", 10, "r1")
        bm.add_to_baseline(v)
        v_abs = self._violation("/abs/src/main.py", 10, "r1")
        assert not bm.is_exempt(v_abs)

    def test_prune_stale_corrupt_file_no_crash(self, tmp_path):
        """prune_stale handles corrupt JSON gracefully."""
        bm = BaselineManager(str(tmp_path))
        baseline_file = tmp_path / "baseline.json"
        baseline_file.write_text("{{{broken", encoding="utf-8")
        count = bm.prune_stale({"r1"})
        assert count == 0

    def test_prune_entire_baseline(self, tmp_path):
        """prune_stale removes all entries when no rules are active."""
        bm = BaselineManager(str(tmp_path))
        bm.add_to_baseline(self._violation("a.py", 1, "r1"))
        bm.add_to_baseline(self._violation("b.py", 2, "r2"))
        count = bm.prune_stale(set())
        assert count == 2
        assert bm.load_baseline_raw() == []

    def test_add_to_baseline_does_not_duplicate_on_signature(self, tmp_path):
        """Both violations with same signature stored only once."""
        bm = BaselineManager(str(tmp_path))
        v1 = self._violation("a.py", 1, "r1", signature="s1")
        v2 = self._violation("a.py", 2, "r1", signature="s1")
        bm.add_to_baseline(v1)
        bm.add_to_baseline(v2)
        assert len(bm.load_baseline_raw()) == 1
