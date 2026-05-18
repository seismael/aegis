"""
Shared constants for the Aegis governance engine.
"""

# Directories to skip during file walking and dependency analysis.
# These are typically virtual environments, caches, or configuration directories.
IGNORE_DIRS: frozenset[str] = frozenset(
    {".venv", "node_modules", ".git", ".aegis", "__pycache__"}
)

# Language-to-extension mapping shared across analyzers.
# Keys are short language codes used in Rule.language.
# Values are the corresponding file extensions.
LANG_EXT_MAP: dict[str, str] = {
    "py": ".py",
    "ts": ".ts",
    "tsx": ".tsx",
    "js": ".js",
    "jsx": ".jsx",
    "rs": ".rs",
}
