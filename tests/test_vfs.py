from aegis.domain.evaluation.vfs import SpeculativeVFS


class TestSpeculativeVFS:
    """Tier 1: V-FS Unit Tests (Isolation & Atomic Integrity)."""

    def test_overlay_isolation(self, tmp_path):
        """Verify that staging a change does not modify the real disk."""
        vfs = SpeculativeVFS(str(tmp_path))
        f = tmp_path / "logic.py"
        f.write_text("original", encoding="utf-8")

        vfs.stage_change("logic.py", "modified")

        # Overlay should have new content
        assert vfs.read("logic.py") == "modified"
        # Real disk should still have original
        assert f.read_text(encoding="utf-8") == "original"

    def test_read_through_correctness(self, tmp_path):
        """Verify that V-FS correctly merges disk state with overlay."""
        vfs = SpeculativeVFS(str(tmp_path))
        (tmp_path / "existing.py").write_text("disk_content", encoding="utf-8")

        # Read file not in overlay -> should come from disk
        assert vfs.read("existing.py") == "disk_content"

    def test_atomic_commit(self, tmp_path):
        """Verify that commit() physically writes to disk and clears overlay."""
        vfs = SpeculativeVFS(str(tmp_path))
        vfs.stage_change("new_file.py", "content")

        f = tmp_path / "new_file.py"
        assert not f.exists()

        vfs.commit("new_file.py")

        assert f.exists()
        assert f.read_text(encoding="utf-8") == "content"
        assert not vfs.is_staged("new_file.py")

    def test_discard_clears_overlay(self, tmp_path):
        vfs = SpeculativeVFS(str(tmp_path))
        vfs.stage_change("temp.py", "trash")
        assert vfs.is_staged("temp.py")

        vfs.discard("temp.py")
        assert not vfs.is_staged("temp.py")

    def test_normalize_path_consistency(self, tmp_path):
        """Verify cross-platform path normalization (forward slashes)."""
        vfs = SpeculativeVFS(str(tmp_path))

        # Absolute path within root
        abs_path = str(tmp_path / "subdir" / "file.py")
        normalized = vfs._normalize_path(abs_path)

        assert "\\" not in normalized
        assert normalized == "subdir/file.py"
