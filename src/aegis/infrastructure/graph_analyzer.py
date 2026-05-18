import ast
import os
from collections import defaultdict

from aegis.core.constants import IGNORE_DIRS
from aegis.core.models.governance import Rule
from aegis.domain.evaluation.ports import ArchitecturalViolation, GraphAnalyzerInterface


class GraphAnalyzer(GraphAnalyzerInterface):
    """
    Cross-file dependency graph analyzer using Python's ast module.
    Builds a directed adjacency graph of all imports across the workspace
    and detects disallowed-import and circular-dependency violations.
    """

    def analyze_graph(
        self, root_dir: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        violations: list[ArchitecturalViolation] = []
        adjacency, file_imports = self.build_import_graph(root_dir)

        for rule in rules:
            if not rule.query:
                continue

            if rule.query == "disallowed_import":
                violations.extend(self._check_disallowed_imports(file_imports, rule))
            elif rule.query == "circular_dependency":
                violations.extend(
                    self._check_circular_dependencies(adjacency, file_imports, rule)
                )

        return violations

    def build_import_graph(
        self, root_dir: str
    ) -> tuple[dict[str, set[str]], dict[str, list[tuple[int, str]]]]:
        """
        Walks the workspace and builds:
        - adjacency: module_name -> set of imported module_names
        - file_imports: module_name -> list of (line_number, imported_module)

        Returns empty dicts if no Python files found.
        """
        adjacency: dict[str, set[str]] = defaultdict(set)
        file_imports: dict[str, list[tuple[int, str]]] = defaultdict(list)

        for root, _, files in os.walk(root_dir):
            if any(x in root for x in IGNORE_DIRS):
                continue

            for file in files:
                if not file.endswith(".py"):
                    continue

                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, root_dir)
                module = rel_path.replace(os.sep, ".")[:-3]
                if module.endswith(".__init__"):
                    module = module[: -len(".__init__")]

                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                except (UnicodeDecodeError, PermissionError):
                    continue

                try:
                    tree = ast.parse(content, filename=file_path)
                except SyntaxError:
                    continue

                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            root_pkg = alias.name.split(".")[0]
                            if root_pkg != module:
                                adjacency[module].add(root_pkg)
                                file_imports[module].append((node.lineno, alias.name))
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            root_pkg = node.module.split(".")[0]
                            if root_pkg != module:
                                adjacency[module].add(root_pkg)
                                file_imports[module].append((node.lineno, node.module))

        return adjacency, file_imports

    def _check_disallowed_imports(
        self,
        file_imports: dict[str, list[tuple[int, str]]],
        rule: Rule,
    ) -> list[ArchitecturalViolation]:
        """
        Flags imports from metadata.source namespace into metadata.target namespace.
        E.g., domain modules importing infrastructure modules.
        """
        violations: list[ArchitecturalViolation] = []
        source_ns = rule.metadata.get("source", "")
        target_ns = rule.metadata.get("target", "")

        if not source_ns or not target_ns:
            return violations

        for module, imports in file_imports.items():
            if not module.startswith(source_ns):
                continue

            for line, imported in imports:
                if imported.startswith(target_ns):
                    violations.append(
                        ArchitecturalViolation(
                            file=module.replace(".", os.sep) + ".py",
                            line=line,
                            rule_id=rule.id,
                            description=(
                                f"{rule.description}: {module} imports {imported}"
                            ),
                            severity=rule.severity.value,
                        )
                    )

        return violations

    def _check_circular_dependencies(
        self,
        adjacency: dict[str, set[str]],
        file_imports: dict[str, list[tuple[int, str]]],
        rule: Rule,
    ) -> list[ArchitecturalViolation]:
        """
        Detects circular dependencies using DFS with a recursion stack.
        Returns violations for each edge that completes a cycle.
        """
        violations: list[ArchitecturalViolation] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def dfs(node: str, path: list[str]) -> None:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in adjacency.get(node, set()):
                if neighbor not in adjacency and neighbor not in adjacency.values():
                    continue
                if neighbor not in visited:
                    dfs(neighbor, path + [neighbor])
                elif neighbor in rec_stack:
                    # Found a cycle — report the edge
                    for mod, imports in file_imports.items():
                        if mod == node:
                            for line, imported in imports:
                                if imported == neighbor:
                                    violations.append(
                                        ArchitecturalViolation(
                                            file=mod.replace(".", os.sep) + ".py",
                                            line=line,
                                            rule_id=rule.id,
                                            description=(
                                                f"{rule.description}: "
                                                f"circular: {node} -> {neighbor}"
                                            ),
                                            severity=rule.severity.value,
                                        )
                                    )

            rec_stack.discard(node)

        for module in list(adjacency.keys()):
            if module not in visited:
                dfs(module, [module])

        return violations
