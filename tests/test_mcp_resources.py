from unittest.mock import MagicMock, patch

import pytest

from aegis.kernel.server import AegisKernel


@pytest.fixture
def kernel():
    """AegisKernel with a mocked container."""
    k = AegisKernel()
    mock_container = MagicMock()
    mock_container.workspace_root = "/fake/project"
    k.container = mock_container
    return k


class TestMCPResources:
    """Test suite for MCP Resource endpoints."""

    @pytest.mark.asyncio
    async def test_all_governance_resources_registered(self, kernel):
        """Verify all governance artifact resources are registered."""
        resources = await kernel.mcp.list_resources()
        uris = [str(r.uri) for r in resources]
        assert "aegis://rules" in uris
        assert "aegis://baseline" in uris
        assert "aegis://evolution" in uris
        assert "aegis://spec" in uris

    @pytest.mark.asyncio
    async def test_resources_have_description(self, kernel):
        """Each resource should carry a human-readable description."""
        resources = await kernel.mcp.list_resources()
        for r in resources:
            if str(r.uri).startswith("aegis://"):
                assert r.description, f"Resource {r.uri} missing description"

    @pytest.mark.asyncio
    async def test_resource_content_returned(self, kernel):
        """Verify read_resource returns content for existing files."""
        # Use patch on Path.exists and Path.read_text
        with patch("aegis.kernel.server.Path.exists", return_value=True):
            with patch("aegis.kernel.server.Path.is_dir", return_value=False):
                with patch(
                    "aegis.kernel.server.Path.read_text", return_value="rules: []"
                ):
                    results = await kernel.mcp.read_resource("aegis://rules")
        assert len(results) == 1
        content = results[0].content
        assert isinstance(content, str)
        assert "rules:" in content

    @pytest.mark.asyncio
    async def test_rules_resource_not_found(self, kernel):
        """Missing rules.yaml returns ERROR."""
        with patch("aegis.kernel.server.Path.exists", return_value=False):
            with patch("aegis.kernel.server.Path.is_dir", return_value=False):
                results = await kernel.mcp.read_resource("aegis://rules")
        assert "FILE_NOT_FOUND" in results[0].content

    @pytest.mark.asyncio
    async def test_rules_resource_directory_mode(self, kernel):
        """rules/ directory with yaml files returns combined content."""
        with patch("aegis.kernel.server.Path.is_dir", return_value=True):
            mock_file = MagicMock()
            mock_file.is_file.return_value = True
            mock_file.suffix = ".yaml"
            mock_file.name = "arch.yaml"
            mock_file.relative_to.return_value = "arch.yaml"
            mock_file.read_text.return_value = "rules: [- id: arch1]"

            with patch("aegis.kernel.server.Path.rglob", return_value=[mock_file]):
                results = await kernel.mcp.read_resource("aegis://rules")
        assert "arch1" in results[0].content

    @pytest.mark.asyncio
    async def test_rules_resource_directory_empty(self, kernel):
        """Empty rules/ directory returns WARN."""
        with patch("aegis.kernel.server.Path.is_dir", return_value=True):
            with patch("aegis.kernel.server.Path.rglob", return_value=[]):
                results = await kernel.mcp.read_resource("aegis://rules")
        assert "WARN" in results[0].content
        assert "empty" in results[0].content

    @pytest.mark.asyncio
    async def test_rules_resource_directory_read_error(self, kernel):
        """Read error in rules/ directory is non-fatal per-file."""
        with patch("aegis.kernel.server.Path.is_dir", return_value=True):
            mock_file = MagicMock()
            mock_file.is_file.return_value = True
            mock_file.suffix = ".yaml"
            mock_file.name = "bad.yaml"
            mock_file.relative_to.return_value = "bad.yaml"
            mock_file.read_text.side_effect = OSError("denied")

            with patch("aegis.kernel.server.Path.rglob", return_value=[mock_file]):
                results = await kernel.mcp.read_resource("aegis://rules")
        assert "ERROR" in results[0].content or "bad.yaml" in results[0].content

    @pytest.mark.asyncio
    async def test_rules_resource_read_error(self, kernel):
        """rules.yaml read error returns ERROR."""
        with patch("aegis.kernel.server.Path.is_dir", return_value=False):
            with patch("aegis.kernel.server.Path.exists", return_value=True):
                with patch(
                    "aegis.kernel.server.Path.read_text", side_effect=OSError("denied")
                ):
                    results = await kernel.mcp.read_resource("aegis://rules")
        assert "READ_FAILED" in results[0].content
