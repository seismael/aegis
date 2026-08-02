"""
MCP Ecosystem Adapter for Aegis Kernel.
Integrates Aegis governance via Model Context Protocol.
"""

from aegis.kernel.server import AegisKernel


class MCPAdapter:
    """
    FastMCP Microkernel Adapter for Aegis governance.

    Wraps the AegisKernel MCP server for ecosystem integration.
    Provides check_architecture, plan_architecture, query_graph,
    and all other kernel tools via the Model Context Protocol.
    """

    def __init__(self, workspace_root: str | None = None):
        self._kernel = AegisKernel(workspace_root=workspace_root)

    @property
    def kernel(self) -> AegisKernel:
        return self._kernel

    async def check_architecture(self, files_modified: list[str], **kwargs) -> str:
        return await self._kernel.check_architecture(files_modified, **kwargs)

    async def plan_architecture(self, intent: str, **kwargs) -> str:
        return await self._kernel.plan_architecture(intent, **kwargs)

    async def query_graph(self, query_type: str, **kwargs) -> str:
        return await self._kernel.query_graph(query_type, **kwargs)

    def run(self, transport: str = "stdio", host: str = "127.0.0.1", port: int = 8000):
        self._kernel.run(transport=transport, host=host, port=port)


__all__ = ["MCPAdapter", "AegisKernel"]
