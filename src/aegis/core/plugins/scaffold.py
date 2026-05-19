"""Plugin scaffold generator for Aegis plugin SDK."""

import os

_PLUGIN_TEMPLATE = '''\"\"\"
Aegis plugin: {name}

Register custom analyzers and MCP tools for architectural governance.
See: https://github.com/your-org/aegis#plugins
\"\"\"

from aegis.domain.evaluation.ports import ArchitecturalViolation, RuleAnalyzerInterface
from aegis.domain.policy.models import Rule


# ── Hook 1: Custom Analyzers ──────────────────────────────────────────────

class MyAnalyzer(RuleAnalyzerInterface):
    \"\"\"Example custom analyzer. Replace with your own logic.\"\"\"

    def analyze_file(
        self, file_path: str, content: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        \"\"\"Analyze a single file and return violations.\"\"\"
        # Example: flag TODO comments as violations
        violations = []
        for i, line in enumerate(content.splitlines(), start=1):
            if "TODO" in line and rules:
                for r in rules:
                    if r.id == "no-todo":
                        violations.append(
                            ArchitecturalViolation(
                                file=file_path,
                                line=i,
                                rule_id=r.id,
                                description="TODO comment found",
                            )
                        )
        return violations


def register_analyzers() -> list[RuleAnalyzerInterface]:
    \"\"\"Return custom analyzer instances.\"\"\"
    return [MyAnalyzer()]


# ── Hook 2: Custom MCP Tools (optional) ──────────────────────────────────

def register_mcp_tools() -> list:
    \"\"\"Return custom MCP tool functions (optional).\"\"\"
    return []
'''


def create_plugin_scaffold(plugin_dir: str, name: str) -> str:
    """Create a plugin scaffold file at plugin_dir/{name}.py.

    Returns the path to the created file.
    Raises ValueError if the file already exists or the name is invalid.
    """
    if not name or not name.replace("_", "").replace("-", "").isidentifier():
        raise ValueError(
            f"Invalid plugin name: '{name}'. Use letters, digits, underscores."
        )
    filename = name.replace("-", "_")
    filepath = os.path.join(plugin_dir, f"{filename}.py")
    if os.path.exists(filepath):
        raise ValueError(f"Plugin already exists: {filepath}")
    os.makedirs(plugin_dir, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(_PLUGIN_TEMPLATE.format(name=name))
    return filepath
