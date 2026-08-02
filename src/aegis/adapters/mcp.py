"""
MCP Ecosystem Adapter for Aegis Kernel.
Integrates Aegis governance via Model Context Protocol.
"""

from aegis.kernel.server import AegisKernel

MCPAdapter = AegisKernel

__all__ = ["MCPAdapter", "AegisKernel"]
