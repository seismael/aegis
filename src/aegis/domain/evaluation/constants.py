IGNORE_DIRS = frozenset(
    {
        ".venv",
        "node_modules",
        ".git",
        ".aegis",
        "__pycache__",
        ".tox",
        "dist",
        "build",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "tests",
    }
)

LANG_EXT_MAP = {
    "python": ".py",
    "typescript": ".ts",
    "javascript": ".js",
    "rust": ".rs",
    "go": ".go",
    "tsx": ".tsx",
    "jsx": ".jsx",
}
