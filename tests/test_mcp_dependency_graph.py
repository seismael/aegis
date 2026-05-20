from unittest.mock import MagicMock

import pytest

from aegis.infrastructure.graph_analyzer import GraphAnalyzer
from aegis.kernel.server import AegisKernel


class TestMCPDependencyGraph:
    """
    Test suite for the get_dependency_graph MCP tool.
    """

    @pytest.mark.asyncio
    async def test_dependency_graph_returns_info(self, tmp_path):
        """Verify get_dependency_graph returns module info when module exists."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "__init__.py").write_text("", encoding="utf-8")
        (src / "main.py").write_text(
            "from src.utils import helper\nx = 1\n", encoding="utf-8"
        )
        (src / "utils.py").write_text("def helper(): pass\n", encoding="utf-8")

        kernel = AegisKernel()
        # Replace the real container with a mock
        mock_container = MagicMock()
        mock_container.workspace_root = str(tmp_path)
        mock_container.graph_analyzer = GraphAnalyzer()
        kernel.container = mock_container

        result = await kernel._get_dependency_graph("main")
        assert "main" in result

    @pytest.mark.asyncio
    async def test_dependency_graph_no_modules(self, tmp_path):
        """Verify get_dependency_graph handles empty workspace."""
        kernel = AegisKernel()
        mock_container = MagicMock()
        mock_container.workspace_root = str(tmp_path)
        mock_container.graph_analyzer = GraphAnalyzer()
        kernel.container = mock_container

        result = await kernel._get_dependency_graph("nonexistent")
        assert "no python modules" in result.lower() or "not found" in result.lower()
