import os
from unittest.mock import patch

from aegis.domain.evaluation.analyzers.graph import GraphAnalyzer
from aegis.domain.policy.models import EnforcementMode, EngineType, Rule, Severity


class TestGraphAnalyzer:
    """Test suite for the GraphAnalyzer (cross-file dependency graph)."""

    def _make_rule(self, rid, query, source="", target=""):
        return Rule(
            id=rid,
            description=f"Rule: {rid}",
            engine_type=EngineType.GRAPH,
            query=query,
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
            metadata={"source": source, "target": target},
        )

    def test_disallowed_import_detected(self, tmp_path):
        domain = tmp_path / "domain"
        domain.mkdir()
        (domain / "__init__.py").write_text("", encoding="utf-8")
        (domain / "main.py").write_text(
            "from infrastructure.database import connect\nx = 1\n",
            encoding="utf-8",
        )

        infra = tmp_path / "infrastructure"
        infra.mkdir()
        (infra / "__init__.py").write_text("", encoding="utf-8")
        (infra / "database.py").write_text("def connect(): pass\n", encoding="utf-8")

        analyzer = GraphAnalyzer()
        rule = self._make_rule(
            "no-infra-in-domain",
            "disallowed_import",
            source="domain",
            target="infrastructure",
        )
        violations = analyzer.analyze_graph(str(tmp_path), [rule])
        assert len(violations) == 1
        assert violations[0].rule_id == "no-infra-in-domain"

    def test_disallowed_import_clean(self, tmp_path):
        domain = tmp_path / "domain"
        domain.mkdir()
        (domain / "__init__.py").write_text("", encoding="utf-8")
        (domain / "main.py").write_text(
            "from domain.models import User\nx = 1\n",
            encoding="utf-8",
        )

        analyzer = GraphAnalyzer()
        rule = self._make_rule(
            "no-infra-in-domain",
            "disallowed_import",
            source="domain",
            target="infrastructure",
        )
        violations = analyzer.analyze_graph(str(tmp_path), [rule])
        assert len(violations) == 0

    def test_circular_dependency_detected(self, tmp_path):
        (tmp_path / "a.py").write_text("from b import foo\nx = 1\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("from a import bar\ny = 2\n", encoding="utf-8")

        analyzer = GraphAnalyzer()
        rule = self._make_rule("no-circular", "circular_dependency")
        violations = analyzer.analyze_graph(str(tmp_path), [rule])
        assert len(violations) >= 1
        assert violations[0].rule_id == "no-circular"

    def test_no_circular_no_violations(self, tmp_path):
        (tmp_path / "a.py").write_text("from b import foo\nx = 1\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("y = 2\n", encoding="utf-8")

        analyzer = GraphAnalyzer()
        rule = self._make_rule("no-circular", "circular_dependency")
        violations = analyzer.analyze_graph(str(tmp_path), [rule])
        assert len(violations) == 0

    def test_build_import_graph_returns_adjacency(self, tmp_path):
        (tmp_path / "a.py").write_text("from b import foo\nx = 1\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("from c import bar\ny = 2\n", encoding="utf-8")
        (tmp_path / "c.py").write_text("z = 3\n", encoding="utf-8")

        analyzer = GraphAnalyzer()
        adjacency, file_imports = analyzer.build_import_graph(str(tmp_path))

        assert "a" in adjacency
        assert "b" in adjacency
        assert "b" in adjacency["a"]
        assert "c" in adjacency["b"]
        assert len(file_imports["a"]) == 1
        assert file_imports["a"][0][1] == "b"

    def test_build_import_graph_empty_dir(self, tmp_path):
        analyzer = GraphAnalyzer()
        adjacency, file_imports = analyzer.build_import_graph(str(tmp_path))
        assert adjacency == {}
        assert file_imports == {}

    def test_build_import_graph_ignores_excluded_dirs(self, tmp_path):
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "lib.py").write_text("import bad_thing\n", encoding="utf-8")
        (tmp_path / "main.py").write_text(
            "from utils import helper\n", encoding="utf-8"
        )
        (tmp_path / "utils.py").write_text("def helper(): pass\n", encoding="utf-8")

        analyzer = GraphAnalyzer()
        adjacency, file_imports = analyzer.build_import_graph(str(tmp_path))

        assert ".venv.lib" not in adjacency
        assert "main" in adjacency
        assert "utils" in adjacency["main"]

    def test_ignores_venv_and_node_modules(self, tmp_path):
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "lib.py").write_text(
            "import bad_thing\n", encoding="utf-8"
        )
        (tmp_path / "main.py").write_text("x = 1\n", encoding="utf-8")

        analyzer = GraphAnalyzer()
        rule = self._make_rule(
            "no-infra",
            "disallowed_import",
            source="domain",
            target="infrastructure",
        )
        violations = analyzer.analyze_graph(str(tmp_path), [rule])
        assert violations == []

    # --- Deeper edge cases ---

    def test_empty_rules_list(self, tmp_path):
        """Empty rules list returns no violations."""
        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
        analyzer = GraphAnalyzer()
        violations = analyzer.analyze_graph(str(tmp_path), [])
        assert violations == []

    def test_unknown_query_returns_empty(self, tmp_path):
        """Unrecognized query type produces no violations (no crash)."""
        (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
        analyzer = GraphAnalyzer()
        rule = self._make_rule("r1", "unknown_query_type")
        violations = analyzer.analyze_graph(str(tmp_path), [rule])
        assert violations == []

    def test_self_import_not_counted(self, tmp_path):
        """Module importing itself is not added to adjacency."""
        (tmp_path / "a.py").write_text("import a\nx = 1\n", encoding="utf-8")
        analyzer = GraphAnalyzer()
        adjacency, _ = analyzer.build_import_graph(str(tmp_path))
        # a importing a should be excluded
        assert adjacency.get("a", set()) == set()

    def test_non_python_files_ignored(self, tmp_path):
        """Non-.py files are not included in the graph."""
        (tmp_path / "main.py").write_text(
            "from utils import helper\n", encoding="utf-8"
        )
        (tmp_path / "utils.py").write_text("def helper(): pass\n", encoding="utf-8")
        (tmp_path / "data.json").write_text("{}", encoding="utf-8")
        (tmp_path / "script.sh").write_text("echo hi", encoding="utf-8")
        analyzer = GraphAnalyzer()
        adjacency, _ = analyzer.build_import_graph(str(tmp_path))
        assert "main" in adjacency
        assert "data.json" not in adjacency
        assert "script.sh" not in adjacency

    def test_syntax_error_skipped(self, tmp_path):
        """File with syntax errors is skipped without crashing."""
        (tmp_path / "broken.py").write_text(
            "this is not valid python @@@", encoding="utf-8"
        )
        (tmp_path / "good.py").write_text(
            "from utils import helper\n", encoding="utf-8"
        )
        (tmp_path / "utils.py").write_text("def helper(): pass\n", encoding="utf-8")
        analyzer = GraphAnalyzer()
        # Should not crash; good.py still analyzed
        adjacency, _ = analyzer.build_import_graph(str(tmp_path))
        assert "good" in adjacency
        assert "broken" not in adjacency

    def test_transitive_cycle_detected(self, tmp_path):
        """a->b->c->a detected as circular."""
        (tmp_path / "a.py").write_text("from b import x\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("from c import y\n", encoding="utf-8")
        (tmp_path / "c.py").write_text("from a import z\n", encoding="utf-8")
        analyzer = GraphAnalyzer()
        rule = self._make_rule("no-circular", "circular_dependency")
        violations = analyzer.analyze_graph(str(tmp_path), [rule])
        assert len(violations) >= 1

    def test_nested_package_module_name(self, tmp_path):
        """Nested package produces dotted module name."""
        pkg = tmp_path / "pkg" / "sub"
        pkg.mkdir(parents=True)
        (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "mod.py").write_text("import os\n", encoding="utf-8")
        analyzer = GraphAnalyzer()
        adjacency, _ = analyzer.build_import_graph(str(tmp_path))
        assert "pkg.sub.mod" in adjacency

    def test_init_py_normalized(self, tmp_path):
        """__init__.py maps to parent package name."""
        (tmp_path / "pkg").mkdir()
        (tmp_path / "pkg" / "__init__.py").write_text(
            "from os import path\n", encoding="utf-8"
        )
        (tmp_path / "pkg" / "mod.py").write_text("x = 1\n", encoding="utf-8")
        analyzer = GraphAnalyzer()
        adjacency, _ = analyzer.build_import_graph(str(tmp_path))
        assert "pkg" in adjacency
        assert "pkg.__init__" not in adjacency

    def test_disallowed_import_no_metadata(self, tmp_path):
        """Disallowed import rule without source/target metadata returns no results."""
        (tmp_path / "a.py").write_text("import b\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("x = 1\n", encoding="utf-8")
        analyzer = GraphAnalyzer()
        rule = Rule(
            id="no-cross",
            description="test",
            query="disallowed_import",
            engine_type=EngineType.GRAPH,
            metadata={},
        )
        violations = analyzer.analyze_graph(str(tmp_path), [rule])
        assert violations == []

    def test_unicode_file_skipped_gracefully(self, tmp_path):
        """Binary/unicode file that can't be decoded is skipped."""
        (tmp_path / "main.py").write_text("from os import path\n", encoding="utf-8")
        (tmp_path / "data.py").write_bytes(b"\xff\xfe\x00\x01")
        analyzer = GraphAnalyzer()
        # Should not crash
        adjacency, _ = analyzer.build_import_graph(str(tmp_path))
        assert "main" in adjacency

    def test_multiple_imports_in_one_file(self, tmp_path):
        """Multiple imports from one file are all tracked."""
        (tmp_path / "a.py").write_text(
            "import b\nimport c\nfrom d import e\n", encoding="utf-8"
        )
        (tmp_path / "b.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "c.py").write_text("x = 1\n", encoding="utf-8")
        (tmp_path / "d.py").write_text("e = 1\n", encoding="utf-8")
        analyzer = GraphAnalyzer()
        adjacency, _ = analyzer.build_import_graph(str(tmp_path))
        assert adjacency.get("a") == {"b", "c", "d"}

    def test_very_large_python_file_skipped(self, tmp_path):
        """File larger than _MAX_FILE_BYTES is skipped."""
        (tmp_path / "main.py").write_text("from os import path\n", encoding="utf-8")
        (tmp_path / "huge.py").write_text("x = 1\n", encoding="utf-8")
        analyzer = GraphAnalyzer()
        with patch("aegis.infrastructure.graph_analyzer._MAX_FILE_BYTES", 5):
            adjacency, _ = analyzer.build_import_graph(str(tmp_path))
        # huge.py (5 bytes) exceeds 5-byte limit, main.py (17 bytes) also skipped
        assert "huge" not in adjacency
        assert "main" not in adjacency

    def test_file_size_check_large_file_skipped_small_kept(self, tmp_path):
        """Small file processed, large file skipped."""
        (tmp_path / "small.py").write_text("from os import path\n", encoding="utf-8")
        (tmp_path / "large.py").write_text(
            "# " + "x" * 2000 + "\nx = 1\n", encoding="utf-8"
        )
        analyzer = GraphAnalyzer()
        with patch("aegis.infrastructure.graph_analyzer._MAX_FILE_BYTES", 500):
            adjacency, _ = analyzer.build_import_graph(str(tmp_path))
        assert "small" in adjacency
        assert "large" not in adjacency

    def test_file_size_check_oserror_skipped(self, tmp_path):
        """OSError during file size check is handled gracefully."""
        main = tmp_path / "main.py"
        broken = tmp_path / "broken.py"
        main.write_text("from utils import helper\n", encoding="utf-8")
        (tmp_path / "utils.py").write_text("def helper(): pass\n", encoding="utf-8")
        broken.write_text("y = 2\n", encoding="utf-8")

        real_getsize = os.path.getsize

        def _fake_getsize(path):
            if os.fspath(path).endswith("broken.py"):
                raise OSError("denied")
            return real_getsize(path)

        analyzer = GraphAnalyzer()
        with patch(
            "aegis.infrastructure.graph_analyzer.os.path.getsize",
            side_effect=_fake_getsize,
        ):
            adjacency, _ = analyzer.build_import_graph(str(tmp_path))
        assert "broken" not in adjacency
        assert "main" in adjacency

    def test_null_bytes_in_file_skipped(self, tmp_path):
        """File with null bytes is skipped gracefully."""
        (tmp_path / "good.py").write_text("from os import path\n", encoding="utf-8")
        (tmp_path / "binary.py").write_bytes(b"x = 1\x00\x00\x00")
        analyzer = GraphAnalyzer()
        adjacency, _ = analyzer.build_import_graph(str(tmp_path))
        # binary.py skipped due to null bytes in ast.parse, good.py ok
        assert "good" in adjacency

    def test_empty_python_file_no_crash(self, tmp_path):
        """Empty .py file produces no adjacency entry."""
        (tmp_path / "empty.py").write_text("", encoding="utf-8")
        analyzer = GraphAnalyzer()
        adjacency, _ = analyzer.build_import_graph(str(tmp_path))
        assert "empty" not in adjacency

    def test_recursive_import_self_via_init(self, tmp_path):
        """Self-import via __init__ normalization does not crash."""
        pkg = tmp_path / "pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("from pkg import mod\n", encoding="utf-8")
        (pkg / "mod.py").write_text("x = 1\n", encoding="utf-8")
        analyzer = GraphAnalyzer()
        adjacency, _ = analyzer.build_import_graph(str(tmp_path))
        # __init__ normalizes to pkg, self-import excluded
        assert "pkg" not in adjacency or "pkg" not in adjacency.get("pkg", set())

    def test_ignores_non_adjacent_target(self, tmp_path):
        """Neighbor that is not in adjacency nor in any adjacency values is skipped."""
        (tmp_path / "a.py").write_text("import b\nimport c\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("x = 1\n", encoding="utf-8")
        # c.py does not exist — import target missing from graph
        analyzer = GraphAnalyzer()
        adjacency, _ = analyzer.build_import_graph(str(tmp_path))
        assert "a" in adjacency
        # c is in adjacency["a"] since we parsed the import, but module doesn't exist
        assert "b" in adjacency["a"]
