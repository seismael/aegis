"""
Shared constants for the Aegis governance engine.
"""

# Directories to skip during file walking and dependency analysis.
# These are typically virtual environments, caches, or configuration directories.
IGNORE_DIRS: frozenset[str] = frozenset(
    {".venv", "node_modules", ".git", ".aegis", "__pycache__"}
)
