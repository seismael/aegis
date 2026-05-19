"""Tests for the file_watcher polling daemon."""

from aegis.infrastructure.file_watcher import FileWatcher


class TestFileWatcher:
    """Tests for FileWatcher._iter_python_files helper."""

    def test_finds_py_files(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1")
        (tmp_path / "util.py").write_text("y = 2")
        w = FileWatcher(str(tmp_path))
        result = w._iter_python_files()
        assert len(result) == 2

    def test_skips_non_py_files(self, tmp_path):
        (tmp_path / "main.py").write_text("x = 1")
        (tmp_path / "readme.md").write_text("# doc")
        w = FileWatcher(str(tmp_path))
        result = w._iter_python_files()
        assert len(result) == 1

    def test_skips_ignored_dirs(self, tmp_path):
        (tmp_path / ".git" / "hook.py").parent.mkdir(parents=True)
        (tmp_path / ".git" / "hook.py").write_text("")
        (tmp_path / "main.py").write_text("x = 1")
        w = FileWatcher(str(tmp_path))
        result = w._iter_python_files()
        assert len(result) == 1
        assert str(tmp_path / "main.py") in result

    def test_handles_empty_dir(self, tmp_path):
        w = FileWatcher(str(tmp_path))
        result = w._iter_python_files()
        assert result == {}

    def test_handles_nonexistent_dir(self, tmp_path):
        w = FileWatcher(str(tmp_path / "nonexistent"))
        result = w._iter_python_files()
        assert result == {}

    def test_detects_mtime_changes(self, tmp_path):
        """Verifies that different file contents produce different mtime results."""
        f = tmp_path / "main.py"
        f.write_text("x = 1")
        w = FileWatcher(str(tmp_path))
        first = w._iter_python_files()
        import time
        time.sleep(0.01)
        f.write_text("x = 2")
        second = w._iter_python_files()
        assert first[str(f)] != second[str(f)]
