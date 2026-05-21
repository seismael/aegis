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
    Supports agent multi-tenancy via session_id.
    """

    def __init__(self, workspace_root: str):
        self.root = Path(workspace_root)
        # session_id -> { relative_path -> staged_content }
        self._overlay: dict[str, dict[str, str]] = {}
        # session_id -> { relative_path -> quarantine_reason }
        self._quarantine: dict[str, dict[str, str]] = {}

    def _get_session_overlay(self, session_id: str) -> dict[str, str]:
        if session_id not in self._overlay:
            self._overlay[session_id] = {}
        return self._overlay[session_id]

    def _get_session_quarantine(self, session_id: str) -> dict[str, str]:
        if session_id not in self._quarantine:
            self._quarantine[session_id] = {}
        return self._quarantine[session_id]

    def stage_change(
        self, file_path: str, content: str, session_id: str = "default"
    ) -> str:
        """
        Stages a proposed change in the virtual overlay.
        Returns the normalized relative path.
        """
        rel_path = self._normalize_path(file_path)
        self._get_session_overlay(session_id)[rel_path] = content
        # Clear quarantine on new stage
        q = self._get_session_quarantine(session_id)
        if rel_path in q:
            del q[rel_path]
        return rel_path

    def read(self, file_path: str, session_id: str = "default") -> str:
        """
        Read content from the overlay if staged, otherwise read from real disk.
        """
        rel_path = self._normalize_path(file_path)
        overlay = self._get_session_overlay(session_id)

        if rel_path in overlay:
            return overlay[rel_path]

        full_path = self.root / rel_path
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {rel_path}")

        return full_path.read_text(encoding="utf-8")

    def commit(self, file_path: str, session_id: str = "default") -> bool:
        """
        Physically writes a staged change to the real disk.
        Returns True if a write occurred, False if nothing was staged.
        """
        rel_path = self._normalize_path(file_path)
        overlay = self._get_session_overlay(session_id)

        if rel_path not in overlay:
            return False

        content = overlay[rel_path]
        full_path = self.root / rel_path

        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write
        tmp_path = full_path.with_suffix(f".aegis_tmp_{session_id}")
        try:
            tmp_path.write_text(content, encoding="utf-8")
            os.replace(tmp_path, full_path)
            del overlay[rel_path]
            # Clear quarantine if it existed
            q = self._get_session_quarantine(session_id)
            if rel_path in q:
                del q[rel_path]
            return True
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink()
            raise

    def discard(self, file_path: str, session_id: str = "default") -> bool:
        """Removes a staged change from the overlay without committing."""
        rel_path = self._normalize_path(file_path)
        overlay = self._get_session_overlay(session_id)
        if rel_path in overlay:
            del overlay[rel_path]
            q = self._get_session_quarantine(session_id)
            if rel_path in q:
                del q[rel_path]
            return True
        return False

    def quarantine(
        self, file_path: str, reason: str, session_id: str = "default"
    ) -> None:
        """Marks a staged file as quarantined (blocked from commit)."""
        rel_path = self._normalize_path(file_path)
        q = self._get_session_quarantine(session_id)
        q[rel_path] = reason

    def is_quarantined(self, file_path: str, session_id: str = "default") -> bool:
        rel_path = self._normalize_path(file_path)
        q = self._get_session_quarantine(session_id)
        return rel_path in q

    def is_staged(self, file_path: str, session_id: str = "default") -> bool:
        """Checks if a file has a pending staged change."""
        overlay = self._get_session_overlay(session_id)
        return self._normalize_path(file_path) in overlay

    def _normalize_path(self, file_path: str) -> str:
        """Ensures paths are consistent relative strings with forward slashes."""
        path = Path(file_path)
        if path.is_absolute():
            try:
                path = path.relative_to(self.root)
            except ValueError:
                pass
        return str(path).replace(os.sep, "/")
