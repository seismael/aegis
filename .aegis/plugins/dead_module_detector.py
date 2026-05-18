"""
Aegis Plugin: Dead Module Detector

Performs project-wide analysis to find Python modules that are never imported
by any other module in the workspace.

Use-case: Identifying and cleaning up dead code in large repositories.
"""

import os
import re

from aegis.core.plugins import CustomAnalyzerInterface
from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.policy.models import EnforcementMode, Rule, Severity


class DeadModulePlugin(CustomAnalyzerInterface):
    """
    Scans the entire project to build an import graph and identify isolated modules.
    """

    def register_rules(self) -> list[Rule]:
        """Automatically register the dead-module-detection rule."""
        return [
            Rule(
                id="dead-module-detection",
                description="This module is not imported by any other project module.",
                severity=Severity.LOW,
                mode=EnforcementMode.REPORT,
                category="architecture",
            )
        ]

    def analyze_file(
        self, _file_path: str, _content: str, _rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        """File-level analysis is not used for dead module detection."""
        return []

    def analyze_project(
        self, root_dir: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        violations: list[ArchitecturalViolation] = []

        # Check if our rule is active
        if not any(r.id == "dead-module-detection" for r in rules):
            return []

        all_py_files = []
        all_imports = set()

        # Phase 1: Collect all Python files and all import statements
        for root, _, files in os.walk(root_dir):
            ignore_list = ["venv", ".venv", ".git", "__pycache__", ".aegis"]
            if any(x in root.split(os.sep) for x in ignore_list):
                continue

            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, root_dir)
                    module_name = rel_path.replace(os.sep, ".").replace(".py", "")
                    if module_name.endswith(".__init__"):
                        module_name = module_name[:-9]

                    all_py_files.append((full_path, module_name))

                    try:
                        with open(full_path, encoding="utf-8") as f:
                            content = f.read()
                            # Simple regex for imports
                            imports = re.findall(
                                r"(?:from|import)\s+([\w\.]+)", content
                            )
                            for imp in imports:
                                all_imports.add(imp)
                    except (UnicodeDecodeError, OSError):
                        continue

        # Phase 2: Identify modules that are never in any import statement
        for path, mod in all_py_files:
            file_name = os.path.basename(path)
            if file_name in ["main.py", "app.py", "__init__.py", "setup.py"]:
                continue

            # Simple check: is this module name found as a prefix in any import?
            is_imported = False
            for imp in all_imports:
                if imp == mod or imp.startswith(mod + "."):
                    is_imported = True
                    break

            if not is_imported:
                violations.append(
                    ArchitecturalViolation(
                        file=path,
                        line=1,
                        rule_id="dead-module-detection",
                        description=(
                            f"Dead Module Detected: '{mod}' is not imported. "
                            "Consider removing it or verifying its entry point."
                        ),
                        severity="LOW",
                    )
                )

        return violations

    def provide_remediation(
        self, violation: ArchitecturalViolation, _rule: Rule
    ) -> str | None:
        if violation.rule_id == "dead-module-detection":
            return (
                "Dead Module Detected: This module appears to be dead code. "
                "Verify if it is an external entry point (e.g., a script). "
                "If not, it should be deleted to reduce surface area."
            )
        return None


def register_analyzers() -> list[CustomAnalyzerInterface]:
    return [DeadModulePlugin()]
