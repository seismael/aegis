"""
Aegis Core Graph Analyzer.
Cross-file dependency graph analyzer using Python's ast module.
Zero agent-framework dependencies.
"""

import ast
import os
from abc import ABC, abstractmethod
from collections import defaultdict

from aegis.core.registry import ArchitecturalViolation, Rule
from aegis.core.scoping import IGNORE_DIRS

# Skip files larger than 10 MB to avoid OOM on ast.parse.
_MAX_FILE_BYTES = 10 * 1024 * 1024



class GraphAnalyzerInterface(ABC):
    """Interface for cross-file dependency graph analysis."""

    @abstractmethod
    def analyze_graph(
        self, root_dir: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        pass


class GraphAnalyzer(GraphAnalyzerInterface):
    """
    Cross-file dependency graph analyzer using Python's ast module.
    Builds a directed adjacency graph of all imports across the workspace
    and detects disallowed-import and circular-dependency violations.
    """

    def __init__(self):
        self._cache: dict[str, tuple[float, tuple[dict, dict]]] = {}

    @staticmethod
    def _get_max_file_bytes() -> int:
        import sys

        domain_mod = sys.modules.get("aegis.domain.evaluation.analyzers.graph")
        if domain_mod and hasattr(domain_mod, "_MAX_FILE_BYTES"):
            return domain_mod._MAX_FILE_BYTES
        return _MAX_FILE_BYTES


    def analyze_graph(
        self, root_dir: str, rules: list[Rule]
    ) -> list[ArchitecturalViolation]:
        violations: list[ArchitecturalViolation] = []
        adjacency, file_imports = self.build_import_graph(root_dir)

        for rule in rules:
            if not rule.query:
                continue

            if rule.query == "disallowed_import":
                violations.extend(
                    self._check_disallowed_imports(
                        file_imports, rule, root_dir=root_dir
                    )
                )
            elif rule.query == "circular_dependency":
                violations.extend(
                    self._check_circular_dependencies(
                        adjacency, file_imports, rule, root_dir=root_dir
                    )
                )

        return violations

    def build_import_graph(
        self, root_dir: str
    ) -> tuple[dict[str, set[str]], dict[str, list[tuple[int, str]]]]:
        """
        Builds adjacency list (module -> set of imported modules)
        and file_imports mapping (module -> list of (lineno, imported_module)).
        Cached by directory mtime hash to avoid re-parsing unchanged files.
        """
        # Calculate max mtime of all .py files in root_dir for cache invalidation
        max_mtime = 0.0
        file_count = 0
        try:
            for root, _, files in os.walk(root_dir):
                rel = os.path.relpath(root, root_dir)
                if rel != "." and any(
                    part in IGNORE_DIRS for part in rel.split(os.sep)
                ):
                    continue
                for f in files:
                    if f.endswith(".py"):
                        file_count += 1
                        st = os.path.getmtime(os.path.join(root, f))
                        if st > max_mtime:
                            max_mtime = st
        except OSError:
            pass

        current_hash = hash((max_mtime, file_count))
        if root_dir in self._cache:
            cached_hash, cached_result = self._cache[root_dir]
            if cached_hash == current_hash:
                return cached_result

        adjacency: dict[str, set[str]] = defaultdict(set)
        file_imports: dict[str, list[tuple[int, str]]] = defaultdict(list)

        for root, _, files in os.walk(root_dir):
            rel_root = os.path.relpath(root, root_dir)
            if rel_root != "." and any(
                part in IGNORE_DIRS for part in rel_root.split(os.sep)
            ):
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
                    file_size = os.path.getsize(file_path)
                    if file_size > self._get_max_file_bytes():
                        continue
                except OSError:
                    continue


                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                except (UnicodeDecodeError, PermissionError):
                    continue

                try:
                    tree = ast.parse(content, filename=file_path)
                except (SyntaxError, ValueError):
                    continue

                for node in ast.iter_child_nodes(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name != module:
                                adjacency[module].add(alias.name)
                                file_imports[module].append((node.lineno, alias.name))
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            if node.module != module:
                                adjacency[module].add(node.module)
                                file_imports[module].append((node.lineno, node.module))

        self._cache[root_dir] = (current_hash, (adjacency, file_imports))
        return adjacency, file_imports

    def _module_to_path(self, module: str, root_dir: str = ".") -> str:
        pkg_init = os.path.join(root_dir, module.replace(".", os.sep), "__init__.py")
        if os.path.isfile(pkg_init):
            return os.path.join(module.replace(".", os.sep), "__init__.py")
        return module.replace(".", os.sep) + ".py"

    def _check_disallowed_imports(
        self,
        file_imports: dict[str, list[tuple[int, str]]],
        rule: Rule,
        root_dir: str = ".",
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
            if source_ns not in module.split("."):
                continue

            for line, imported in imports:
                if target_ns in imported.split("."):
                    violations.append(
                        ArchitecturalViolation(
                            file=self._module_to_path(module, root_dir),
                            line=line,
                            rule_id=rule.id,
                            description=(
                                f"{rule.description}: {module} imports {imported}"
                            ),
                            severity=rule.severity.value,
                        )
                    )

        return violations

    def build_dependency_graph(self, root_dir: str, target: str | None = None) -> dict:
        """
        Build a structured dependency graph for the workspace.
        Returns nodes, edges, and tier information.
        """
        adjacency, file_imports = self.build_import_graph(root_dir)

        if target:
            adjacency = {
                k: v
                for k, v in adjacency.items()
                if k.startswith(target) or any(t.startswith(target) for t in v)
            }

        nodes: list[dict] = []
        edges: list[dict] = []
        seen: set[str] = set()

        for module, deps in adjacency.items():
            if module not in seen:
                seen.add(module)
                tier = module.split(".")[0] if "." in module else "root"
                nodes.append({"id": module, "tier": tier})
            for dep in deps:
                edges.append({"source": module, "target": dep})
                if dep not in seen:
                    seen.add(dep)
                    tier = dep.split(".")[0] if "." in dep else "root"
                    nodes.append({"id": dep, "tier": tier})

        tiers: dict[str, list[str]] = {}
        for node in nodes:
            t = node["tier"]
            tiers.setdefault(t, []).append(node["id"])

        return {
            "nodes": nodes,
            "edges": edges,
            "tiers": {k: len(v) for k, v in tiers.items()},
            "total_modules": len(seen),
            "total_edges": len(edges),
        }

    def _check_circular_dependencies(
        self,
        adjacency: dict[str, set[str]],
        file_imports: dict[str, list[tuple[int, str]]],
        rule: Rule,
        root_dir: str = ".",
    ) -> list[ArchitecturalViolation]:
        """
        Detects circular dependencies using iterative DFS with explicit stack.
        Avoids Python recursion limit on deep dependency chains.
        """
        violations: list[ArchitecturalViolation] = []

        all_modules: set[str] = set(adjacency.keys())
        for targets in adjacency.values():
            all_modules.update(targets)

        visited: set[str] = set()
        rec_stack: set[str] = set()

        for start_node in list(adjacency.keys()):
            if start_node in visited:
                continue

            neighbors_iter = iter(adjacency.get(start_node, set()))
            stack = [(start_node, neighbors_iter, [start_node])]
            visited.add(start_node)
            rec_stack.add(start_node)

            while stack:
                node, n_iter, path = stack[-1]

                try:
                    neighbor = next(n_iter)
                except StopIteration:
                    rec_stack.discard(node)
                    stack.pop()
                    continue

                if neighbor not in all_modules:
                    continue
                if neighbor not in visited:
                    visited.add(neighbor)
                    rec_stack.add(neighbor)
                    nn = iter(adjacency.get(neighbor, set()))
                    stack.append((neighbor, nn, path + [neighbor]))
                elif neighbor in rec_stack:
                    for mod, imports in file_imports.items():
                        if mod == node:
                            for line, imported in imports:
                                if imported == neighbor:
                                    violations.append(
                                        ArchitecturalViolation(
                                            file=self._module_to_path(mod, root_dir),
                                            line=line,
                                            rule_id=rule.id,
                                            description=(
                                                f"{rule.description}: "
                                                f"circular: {node} -> {neighbor}"
                                            ),
                                            severity=rule.severity.value,
                                        )
                                    )

        return violations


__all__ = ["GraphAnalyzer", "GraphAnalyzerInterface"]
