"""
Speculative Virtual File System (V-FS) for Aegis v3.0.

Provides an in-memory overlay for file operations, allowing architectural
validation of proposed changes before they are committed to the physical disk.
"""

import os
from pathlib import Path


class SpeculativeVFS:
    """
    A high-speed, in-memory overlay filesystem.
    Facilitates 'In-Flight' validation of architectural changes.
    """

    def __init__(self, workspace_root: str):
        self.root = Path(workspace_root)
        self._overlay: dict[str, str] = {}  # relative_path -> staged_content

    def stage_change(self, file_path: str, content: str) -> str:
        """
        Stages a proposed change in the virtual overlay.
        Returns the normalized relative path.
        """
        rel_path = self._normalize_path(file_path)
        self._overlay[rel_path] = content
        return rel_path

    def read(self, file_path: str) -> str:
        """
        Read content from the overlay if staged, otherwise read from real disk.
        """
        rel_path = self._normalize_path(file_path)
        if rel_path in self._overlay:
            return self._overlay[rel_path]

        full_path = self.root / rel_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {rel_path}")

        return full_path.read_text(encoding="utf-8")

    def commit(self, file_path: str) -> bool:
        """
        Physically writes a staged change to the real disk.
        Returns True if a write occurred, False if nothing was staged.
        """
        rel_path = self._normalize_path(file_path)
        if rel_path not in self._overlay:
            return False

        content = self._overlay[rel_path]
        full_path = self.root / rel_path

        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write
        tmp_path = full_path.with_suffix(".aegis_tmp")
        try:
            tmp_path.write_text(content, encoding="utf-8")
            os.replace(tmp_path, full_path)
            del self._overlay[rel_path]
            return True
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def discard(self, file_path: str) -> bool:
        """Removes a staged change from the overlay without committing."""
        rel_path = self._normalize_path(file_path)
        if rel_path in self._overlay:
            del self._overlay[rel_path]
            return True
        return False

    def is_staged(self, file_path: str) -> bool:
        """Checks if a file has a pending staged change."""
        return self._normalize_path(file_path) in self._overlay

    def _normalize_path(self, file_path: str) -> str:
        """Ensures paths are consistent relative strings with forward slashes."""
        path = Path(file_path)
        if path.is_absolute():
            try:
                path = path.relative_to(self.root)
            except ValueError:
                # Outside root? Keep as-is but warn in a real implementation
                pass
        return str(path).replace(os.sep, "/")
