from datetime import UTC

from aegis.domain.evaluation.baseline import BaselineManager
from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.policy.models import Rule, RuleCategory


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

    def test_security_rule_never_exempt_even_when_baselined(self, tmp_path):
        bm = BaselineManager(str(tmp_path))
        v = self._violation("src/main.py", 10, "sec-rule")
        bm.add_to_baseline(v)
        rule = Rule(
            id="sec-rule", description="secret check", category=RuleCategory.SECURITY
        )
        assert not bm.is_exempt(v, rule=rule)

    def test_security_rule_no_baseline_still_not_exempt(self, tmp_path):
        bm = BaselineManager(str(tmp_path))
        v = self._violation("src/main.py", 10, "sec-rule")
        rule = Rule(
            id="sec-rule", description="secret check", category=RuleCategory.SECURITY
        )
        assert not bm.is_exempt(v, rule=rule)

    def test_architecture_rule_still_exempt_with_baseline(self, tmp_path):
        bm = BaselineManager(str(tmp_path))
        v = self._violation("src/main.py", 10, "arch-rule")
        bm.add_to_baseline(v)
        rule = Rule(
            id="arch-rule", description="arch check", category=RuleCategory.ARCHITECTURE
        )
        assert bm.is_exempt(v, rule=rule)

    def test_is_exempt_no_rule_backward_compat(self, tmp_path):
        bm = BaselineManager(str(tmp_path))
        v = self._violation("src/main.py", 10, "r1")
        bm.add_to_baseline(v)
        assert bm.is_exempt(v)

    # ─── Corruption edge cases ──────────────────────────────────────────────

    def test_load_baseline_non_list_json(self, tmp_path):
        """Non-list JSON (dict) returns empty list."""
        bm = BaselineManager(str(tmp_path))
        (tmp_path / "baseline.json").write_text('{"not": "a list"}', encoding="utf-8")
        assert bm.load_baseline_raw() == []

    def test_load_baseline_scalar_json(self, tmp_path):
        """Scalar JSON (string) returns empty list."""
        bm = BaselineManager(str(tmp_path))
        (tmp_path / "baseline.json").write_text('"just a string"', encoding="utf-8")
        assert bm.load_baseline_raw() == []

    def test_is_exempt_non_list_baseline(self, tmp_path):
        """is_exempt handles non-list baseline without crashing."""
        bm = BaselineManager(str(tmp_path))
        (tmp_path / "baseline.json").write_text('{"not": "a list"}', encoding="utf-8")
        v = self._violation("main.py", 1, "r1")
        assert not bm.is_exempt(v)

    def test_is_exempt_baseline_with_non_dict_entries(self, tmp_path):
        """is_exempt handles baseline entries that aren't dicts."""
        bm = BaselineManager(str(tmp_path))
        import json

        bm.add_to_baseline(self._violation("main.py", 1, "r1"))
        raw = bm.load_baseline_raw()
        raw.append(None)
        raw.append(42)
        raw.append("string")
        (tmp_path / "baseline.json").write_text(json.dumps(raw), encoding="utf-8")
        # _match should skip non-dict entries via .get() safely
        v = self._violation("main.py", 1, "r1")
        assert bm.is_exempt(v)

    def test_save_baseline_with_corrupt_existing(self, tmp_path):
        """save_baseline overwrites corrupt file cleanly."""
        bm = BaselineManager(str(tmp_path))
        (tmp_path / "baseline.json").write_text("corrupt", encoding="utf-8")
        bm.save_baseline([self._violation("a.py", 1, "r1")])
        raw = bm.load_baseline_raw()
        assert len(raw) == 1
        assert raw[0]["rule_id"] == "r1"

    def test_add_to_baseline_with_corrupt_existing(self, tmp_path):
        """add_to_baseline handles corrupt file by overwriting."""
        bm = BaselineManager(str(tmp_path))
        (tmp_path / "baseline.json").write_text("corrupt", encoding="utf-8")
        v = self._violation("a.py", 1, "r1")
        bm.add_to_baseline(v)
        raw = bm.load_baseline_raw()
        assert len(raw) == 1

    def test_prune_stale_with_non_list_baseline(self, tmp_path):
        """prune_stale handles non-list JSON without crashing."""
        bm = BaselineManager(str(tmp_path))
        (tmp_path / "baseline.json").write_text('{"not": "list"}', encoding="utf-8")
        count = bm.prune_stale({"r1"})
        assert count == 0

    def test_is_exempt_baseline_missing_keys(self, tmp_path):
        """Entries missing file/line/rule_id keys don't cause KeyError."""
        bm = BaselineManager(str(tmp_path))
        import json

        (tmp_path / "baseline.json").write_text(
            json.dumps([{"file": "x.py"}]), encoding="utf-8"
        )
        v = self._violation("x.py", 1, "r1")
        assert not bm.is_exempt(v)

    def test_is_exempt_baseline_line_is_none(self, tmp_path):
        """Null line in baseline entry handled gracefully."""
        bm = BaselineManager(str(tmp_path))
        import json

        (tmp_path / "baseline.json").write_text(
            json.dumps([{"file": "x.py", "line": None, "rule_id": "r1"}]),
            encoding="utf-8",
        )
        v = self._violation("x.py", 1, "r1")
        assert not bm.is_exempt(v)

    def test_add_to_baseline_many_entries(self, tmp_path):
        """add_to_baseline handles entries without corruption."""
        bm = BaselineManager(str(tmp_path))
        for i in range(100):
            bm.add_to_baseline(self._violation("f.py", i, f"r{i}"))
        baseline = bm.load_baseline_raw()
        assert len(baseline) == 100

    def test_add_to_baseline_invalid_entry_does_not_corrupt(self, tmp_path):
        """Baseline survives having non-dict entries mixed in."""
        bm = BaselineManager(str(tmp_path))
        import json

        bm.add_to_baseline(self._violation("a.py", 1, "r1"))
        raw = bm.load_baseline_raw()
        raw.append("not a dict")
        (tmp_path / "baseline.json").write_text(json.dumps(raw), encoding="utf-8")
        # Re-load and verify _match skips non-dict entries gracefully
        v = self._violation("a.py", 1, "r1")
        assert bm.is_exempt(v)
        v2 = self._violation("b.py", 2, "r2")
        assert not bm.is_exempt(v2)

    def test_save_baseline_sets_captured_at(self, tmp_path):
        """save_baseline sets captured_at timestamp on all entries."""
        bm = BaselineManager(str(tmp_path))
        violations = [self._violation("a.py", 1, "r1")]
        bm.save_baseline(violations)
        raw = bm.load_baseline_raw()
        assert len(raw) == 1
        assert raw[0]["captured_at"] is not None
        # Verify it's a valid ISO datetime string
        from datetime import datetime

        datetime.fromisoformat(raw[0]["captured_at"])

    def test_add_to_baseline_sets_captured_at(self, tmp_path):
        """add_to_baseline sets captured_at on new entries."""
        bm = BaselineManager(str(tmp_path))
        bm.add_to_baseline(self._violation("a.py", 1, "r1"))
        raw = bm.load_baseline_raw()
        assert raw[0]["captured_at"] is not None

    def test_show_baseline_empty(self, tmp_path):
        """show_baseline returns message when no entries."""
        bm = BaselineManager(str(tmp_path))
        assert bm.show_baseline() == "No baselined violations."

    def test_show_baseline_with_entries(self, tmp_path):
        """show_baseline returns summary by rule_id."""
        bm = BaselineManager(str(tmp_path))
        bm.add_to_baseline(self._violation("a.py", 1, "r1"))
        bm.add_to_baseline(self._violation("b.py", 2, "r1"))
        bm.add_to_baseline(self._violation("c.py", 3, "r2"))
        summary = bm.show_baseline()
        assert "Total baselined violations: 3" in summary
        assert "r1: 2 entries" in summary
        assert "r2: 1 entry" in summary

    def test_expire_old_removes_expired_entries(self, tmp_path):
        """expire_old removes entries older than the threshold."""
        bm = BaselineManager(str(tmp_path))
        from datetime import datetime, timedelta

        old_ts = (datetime.now(UTC) - timedelta(days=100)).isoformat()
        new_ts = datetime.now(UTC).isoformat()
        raw = [
            {"file": "old.py", "line": 1, "rule_id": "r1", "captured_at": old_ts},
            {"file": "new.py", "line": 2, "rule_id": "r1", "captured_at": new_ts},
        ]
        import json

        (tmp_path / "baseline.json").write_text(json.dumps(raw), encoding="utf-8")
        bm.path = str(tmp_path / "baseline.json")

        removed = bm.expire_old(days=30)
        assert removed == 1
        remaining = bm.load_baseline_raw()
        assert len(remaining) == 1
        assert remaining[0]["file"] == "new.py"

    def test_expire_old_preserves_deleted_rules(self, tmp_path):
        """expire_old keeps entries for rules not in active_rule_ids."""
        bm = BaselineManager(str(tmp_path))
        from datetime import datetime, timedelta

        old_ts = (datetime.now(UTC) - timedelta(days=100)).isoformat()
        raw = [
            {
                "file": "dead.py",
                "line": 1,
                "rule_id": "r_deleted",
                "captured_at": old_ts,
            },
            {
                "file": "active.py",
                "line": 2,
                "rule_id": "r_active",
                "captured_at": old_ts,
            },
        ]
        import json

        (tmp_path / "baseline.json").write_text(json.dumps(raw), encoding="utf-8")
        bm.path = str(tmp_path / "baseline.json")

        removed = bm.expire_old(days=30, active_rule_ids={"r_active"})
        # r_deleted preserved, r_active removed
        assert removed == 1
        remaining = bm.load_baseline_raw()
        assert len(remaining) == 1
        assert remaining[0]["rule_id"] == "r_deleted"

    def test_expire_old_no_timestamp_kept_when_active_unknown(self, tmp_path):
        """Entries without captured_at are kept when active_rule_ids is None."""
        bm = BaselineManager(str(tmp_path))
        raw = [
            {"file": "no_ts.py", "line": 1, "rule_id": "r1"},
        ]
        import json

        (tmp_path / "baseline.json").write_text(json.dumps(raw), encoding="utf-8")
        bm.path = str(tmp_path / "baseline.json")

        removed = bm.expire_old(days=1)
        assert removed == 0
        assert len(bm.load_baseline_raw()) == 1

    def test_expire_old_no_timestamp_expired_with_active_ids(self, tmp_path):
        """Entries without captured_at expire when active_rule_ids is provided."""
        bm = BaselineManager(str(tmp_path))
        raw = [
            {"file": "no_ts.py", "line": 1, "rule_id": "r1"},
        ]
        import json

        (tmp_path / "baseline.json").write_text(json.dumps(raw), encoding="utf-8")
        bm.path = str(tmp_path / "baseline.json")

        removed = bm.expire_old(days=1, active_rule_ids={"r1"})
        assert removed == 1
        assert len(bm.load_baseline_raw()) == 0
