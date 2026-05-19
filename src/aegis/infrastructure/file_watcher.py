"""Polling-based file watcher for aegis watch daemon.

Avoids external dependencies by using os.stat mtime polling.
"""

import os
import time
from collections.abc import Callable


def _iter_python_files(root: str) -> dict[str, float]:
    """Walk root and return {path: mtime} for all .py files."""
    result: dict[str, float] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip common non-source directories
        dirnames[:] = [
            d
            for d in dirnames
            if not d.startswith(".")
            and d not in ("__pycache__", "node_modules", "venv", ".venv", ".git")
        ]
        for f in filenames:
            if f.endswith(".py"):
                full = os.path.join(dirpath, f)
                try:
                    st = os.stat(full)
                    result[full] = st.st_mtime
                except OSError:
                    pass
    return result


def watch_files(
    root: str,
    interval: float = 2.0,
    on_change: Callable[[set[str], set[str], set[str]], None] | None = None,
) -> None:
    """Poll root for Python file changes and call on_change with diffs.

    Args:
        root: Directory to watch.
        interval: Poll interval in seconds.
        on_change: Called with (added, modified, removed) path sets each cycle.
    """
    known = _iter_python_files(root)
    try:
        while True:
            time.sleep(interval)
            current = _iter_python_files(root)
            known_paths = set(known)
            current_paths = set(current)

            added = current_paths - known_paths
            removed = known_paths - current_paths
            modified = {
                p
                for p in current_paths & known_paths
                if current[p] != known.get(p)
            }

            if added or removed or modified:
                if on_change:
                    on_change(added, modified, removed)
                known = current
    except KeyboardInterrupt:
        pass
