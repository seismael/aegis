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
        """Verify all four governance artifact resources are registered."""
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
        with patch("aegis.kernel.server.os.path.exists", return_value=True):
            with patch("aegis.kernel.server.open") as mock_open:
                mock_file = MagicMock()
                mock_file.__enter__.return_value.read.return_value = "rules: []"
                mock_open.return_value = mock_file

                results = await kernel.mcp.read_resource("aegis://rules")
        assert len(results) == 1
        content = results[0].content
        assert isinstance(content, str)
        assert "rules:" in content

    @pytest.mark.asyncio
    async def test_rules_resource_not_found(self, kernel):
        """Missing rules.yaml returns ERROR."""
        with patch("aegis.kernel.server.os.path.exists", return_value=False):
            results = await kernel.mcp.read_resource("aegis://rules")
        assert "FILE_NOT_FOUND" in results[0].content

    @pytest.mark.asyncio
    async def test_baseline_resource_not_found(self, kernel):
        """Missing baseline.json returns WARN."""
        with patch("aegis.kernel.server.os.path.exists", return_value=False):
            results = await kernel.mcp.read_resource("aegis://baseline")
        assert "WARN" in results[0].content

    @pytest.mark.asyncio
    async def test_evolution_resource_not_found(self, kernel):
        """Missing evolution_log.json returns WARN."""
        with patch("aegis.kernel.server.os.path.exists", return_value=False):
            results = await kernel.mcp.read_resource("aegis://evolution")
        assert "WARN" in results[0].content

    @pytest.mark.asyncio
    async def test_spec_resource_not_found(self, kernel):
        """Missing SPEC.md returns WARN."""
        with patch("aegis.kernel.server.os.path.exists", return_value=False):
            results = await kernel.mcp.read_resource("aegis://spec")
        assert "WARN" in results[0].content

    @pytest.mark.asyncio
    async def test_rules_resource_directory_mode(self, kernel):
        """rules/ directory with yaml files returns combined content."""
        root = "/fake/project/.aegis/rules"
        with patch("aegis.kernel.server.os.path.isdir", return_value=True):
            with patch(
                "aegis.kernel.server.os.walk",
                return_value=[(root, [], ["arch.yaml", "sec.yaml"])],
            ):
                with patch("aegis.kernel.server.open") as mock_open:
                    mock_file = MagicMock()
                    mock_file.__enter__.return_value.read.side_effect = [
                        "rules:\n  - id: arch1\n",
                        "rules:\n  - id: sec1\n",
                    ]
                    mock_open.return_value = mock_file
                    results = await kernel.mcp.read_resource("aegis://rules")
        assert "arch1" in results[0].content
        assert "sec1" in results[0].content

    @pytest.mark.asyncio
    async def test_rules_resource_directory_empty(self, kernel):
        """Empty rules/ directory returns WARN."""
        root = "/fake/project/.aegis/rules"
        with patch("aegis.kernel.server.os.path.isdir", return_value=True):
            with patch("aegis.kernel.server.os.walk", return_value=[(root, [], [])]):
                results = await kernel.mcp.read_resource("aegis://rules")
        assert "WARN" in results[0].content
        assert "empty" in results[0].content

    @pytest.mark.asyncio
    async def test_rules_resource_directory_read_error(self, kernel):
        """Read error in rules/ directory is non-fatal per-file."""
        root = "/fake/project/.aegis/rules"
        with patch("aegis.kernel.server.os.path.isdir", return_value=True):
            with patch(
                "aegis.kernel.server.os.walk",
                return_value=[(root, [], ["bad.yaml"])],
            ):
                with patch("aegis.kernel.server.open", side_effect=OSError("denied")):
                    results = await kernel.mcp.read_resource("aegis://rules")
        assert "ERROR" in results[0].content or "bad.yaml" in results[0].content

    @pytest.mark.asyncio
    async def test_rules_resource_read_error(self, kernel):
        """rules.yaml read error returns ERROR."""
        with patch("aegis.kernel.server.os.path.isdir", return_value=False):
            with patch("aegis.kernel.server.os.path.exists", return_value=True):
                with patch("aegis.kernel.server.open", side_effect=OSError("denied")):
                    results = await kernel.mcp.read_resource("aegis://rules")
        assert "READ_FAILED" in results[0].content

    @pytest.mark.asyncio
    async def test_baseline_resource_read_error(self, kernel):
        """baseline.json read error returns ERROR."""
        with patch("aegis.kernel.server.os.path.exists", return_value=True):
            with patch("aegis.kernel.server.open", side_effect=OSError("denied")):
                results = await kernel.mcp.read_resource("aegis://baseline")
        assert "READ_FAILED" in results[0].content

    @pytest.mark.asyncio
    async def test_evolution_resource_read_error(self, kernel):
        """evolution_log.json read error returns ERROR."""
        with patch("aegis.kernel.server.os.path.exists", return_value=True):
            with patch("aegis.kernel.server.open", side_effect=OSError("denied")):
                results = await kernel.mcp.read_resource("aegis://evolution")
        assert "READ_FAILED" in results[0].content

    @pytest.mark.asyncio
    async def test_spec_resource_read_error(self, kernel):
        """SPEC.md read error returns ERROR."""
        with patch("aegis.kernel.server.os.path.exists", return_value=True):
            with patch("aegis.kernel.server.open", side_effect=OSError("denied")):
                results = await kernel.mcp.read_resource("aegis://spec")
        assert "READ_FAILED" in results[0].content

    @pytest.mark.asyncio
    async def test_baseline_resource_content_returned(self, kernel):
        """Readable baseline.json returns content."""
        with patch("aegis.kernel.server.os.path.exists", return_value=True):
            with patch("aegis.kernel.server.open") as mock_open:
                mock_file = MagicMock()
                mock_file.__enter__.return_value.read.return_value = (
                    '[{"file": "x.py"}]'
                )
                mock_open.return_value = mock_file
                results = await kernel.mcp.read_resource("aegis://baseline")
        assert "x.py" in results[0].content

    @pytest.mark.asyncio
    async def test_evolution_resource_content_returned(self, kernel):
        """Readable evolution_log.json returns content."""
        with patch("aegis.kernel.server.os.path.exists", return_value=True):
            with patch("aegis.kernel.server.open") as mock_open:
                mock_file = MagicMock()
                mock_file.__enter__.return_value.read.return_value = '{"decisions": []}'
                mock_open.return_value = mock_file
                results = await kernel.mcp.read_resource("aegis://evolution")
        assert "decisions" in results[0].content

    @pytest.mark.asyncio
    async def test_spec_resource_content_returned(self, kernel):
        """Readable SPEC.md returns content."""
        with patch("aegis.kernel.server.os.path.exists", return_value=True):
            with patch("aegis.kernel.server.open") as mock_open:
                mock_file = MagicMock()
                mock_file.__enter__.return_value.read.return_value = (
                    "# Architecture Spec"
                )
                mock_open.return_value = mock_file
                results = await kernel.mcp.read_resource("aegis://spec")
        assert "Architecture Spec" in results[0].content
