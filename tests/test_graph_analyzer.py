from aegis.core.models.governance import EnforcementMode, EngineType, Rule, Severity
from aegis.infrastructure.graph_analyzer import GraphAnalyzer


class TestGraphAnalyzer:
    """
    Test suite for the GraphAnalyzer (cross-file dependency graph).
    """

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
        # domain/main.py imports from infrastructure
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
        assert (
            "domain.main" in violations[0].file or "domain\\main" in violations[0].file
        )

    def test_disallowed_import_clean(self, tmp_path):
        # domain/main.py does NOT import infrastructure
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
        # a.py imports b, b.py imports a → cycle
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
        """Verify build_import_graph returns structured adjacency data."""
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
        """Verify build_import_graph handles directories with no Python files."""
        analyzer = GraphAnalyzer()
        adjacency, file_imports = analyzer.build_import_graph(str(tmp_path))

        assert adjacency == {}
        assert file_imports == {}

    def test_build_import_graph_ignores_excluded_dirs(self, tmp_path):
        """Verify build_import_graph skips .venv and other ignored directories."""
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "lib.py").write_text("import bad_thing\n", encoding="utf-8")
        (tmp_path / "main.py").write_text(
            "from utils import helper\n", encoding="utf-8"
        )
        (tmp_path / "utils.py").write_text("def helper(): pass\n", encoding="utf-8")

        analyzer = GraphAnalyzer()
        adjacency, file_imports = analyzer.build_import_graph(str(tmp_path))

        # .venv content should not appear
        assert ".venv.lib" not in adjacency
        # main.py imports should be found (ignores .venv)
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
        # Should not crash — .venv is ignored
        violations = analyzer.analyze_graph(str(tmp_path), [rule])
        assert violations == []
