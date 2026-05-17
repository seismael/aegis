from unittest.mock import MagicMock, patch

import pytest

from aegis.kernel.server import AegisKernel


class TestMCPTransport:
    """Test suite for MCP transport configuration."""

    def test_default_transport_is_stdio(self):
        """Default run uses stdio transport."""
        kernel = AegisKernel()
        with patch.object(kernel.mcp, "run") as mock_run:
            kernel.run()
            mock_run.assert_called_once()

    def test_sse_transport_does_not_call_stdio(self):
        """SSE transport should not call the stdio run method."""
        kernel = AegisKernel()
        with (
            patch.object(kernel.mcp, "sse_app") as mock_sse,
            patch("uvicorn.run") as mock_uvicorn,
        ):
            kernel.run(transport="sse", host="0.0.0.0", port=9000)
            mock_sse.assert_called_once()
            mock_uvicorn.assert_called_once()
            args, kwargs = mock_uvicorn.call_args
            assert kwargs["host"] == "0.0.0.0"
            assert kwargs["port"] == 9000

    def test_streamable_http_transport(self):
        """streamable-http transport uses the http_app method."""
        kernel = AegisKernel()
        with (
            patch.object(kernel.mcp, "streamable_http_app") as mock_http,
            patch("uvicorn.run") as mock_uvicorn,
        ):
            kernel.run(transport="streamable-http")
            mock_http.assert_called_once()
            mock_uvicorn.assert_called_once()

    def test_invalid_transport_raises(self):
        """Unsupported transport raises ValueError."""
        kernel = AegisKernel()
        with pytest.raises(ValueError, match="Unsupported transport"):
            kernel.run(transport="invalid")

    @patch("argparse.ArgumentParser.parse_args")
    def test_entry_point_parses_transport_arg(self, mock_parse_args):
        """entry_point parses --transport argument."""
        mock_parse_args.return_value = MagicMock(
            transport="stdio", host="127.0.0.1", port=8000
        )
        with patch.object(AegisKernel, "run") as mock_run:
            AegisKernel.entry_point()
            mock_run.assert_called_once_with(
                transport="stdio", host="127.0.0.1", port=8000
            )
