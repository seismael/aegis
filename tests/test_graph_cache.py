import os
import time
import pytest
from aegis.domain.evaluation.analyzers.graph import GraphAnalyzer

class TestGraphCache:
    def test_cache_hit(self, tmp_path):
        # Setup
        (tmp_path / "a.py").write_text("import b", encoding="utf-8")
        (tmp_path / "b.py").write_text("pass", encoding="utf-8")
        
        analyzer = GraphAnalyzer()
        
        # First call - build
        adj1, imports1 = analyzer.build_import_graph(str(tmp_path))
        assert "a" in adj1
        assert "b" in adj1["a"]
        
        # Second call - hit
        # We can verify it's the same object if we want to be sure, 
        # but GraphAnalyzer.build_import_graph returns new dicts usually.
        # However, our cache stores the dicts.
        adj2, imports2 = analyzer.build_import_graph(str(tmp_path))
        assert adj1 is adj2
        assert imports1 is imports2

    def test_cache_invalidation_on_change(self, tmp_path):
        a_py = tmp_path / "a.py"
        a_py.write_text("import b", encoding="utf-8")
        (tmp_path / "b.py").write_text("pass", encoding="utf-8")
        
        analyzer = GraphAnalyzer()
        
        adj1, _ = analyzer.build_import_graph(str(tmp_path))
        assert "b" in adj1["a"]
        
        # Change file and ensure mtime increases
        time.sleep(0.1) # Small sleep for FS resolution
        a_py.write_text("import c", encoding="utf-8")
        (tmp_path / "c.py").write_text("pass", encoding="utf-8")
        
        # Force mtime update if it's too fast
        st = os.stat(str(a_py))
        os.utime(str(a_py), (st.st_atime, st.st_mtime + 1.0))
        
        adj2, _ = analyzer.build_import_graph(str(tmp_path))
        assert "c" in adj2["a"]
        assert "b" not in adj2["a"]
        assert adj1 is not adj2

    def test_cache_different_roots(self, tmp_path):
        root1 = tmp_path / "root1"
        root2 = tmp_path / "root2"
        root1.mkdir()
        root2.mkdir()
        
        (root1 / "a.py").write_text("import b", encoding="utf-8")
        (root2 / "a.py").write_text("import c", encoding="utf-8")
        
        analyzer = GraphAnalyzer()
        
        adj1, _ = analyzer.build_import_graph(str(root1))
        adj2, _ = analyzer.build_import_graph(str(root2))
        
        assert "b" in adj1["a"]
        assert "c" in adj2["a"]
        assert len(analyzer._cache) == 2
