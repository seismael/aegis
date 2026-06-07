import pytest


class TestKernelInit:
    def test_kernel_constructs(self):
        from aegis.kernel.server import AegisKernel

        kernel = AegisKernel()
        assert kernel is not None
        assert kernel.mcp is not None

    def test_kernel_with_custom_root(self, tmp_path):
        from aegis.kernel.server import AegisKernel

        kernel = AegisKernel(workspace_root=str(tmp_path))
        assert kernel.workspace_root == str(tmp_path)

    @pytest.mark.asyncio
    async def test_apply_rules_registration(self):
        from aegis.kernel.server import AegisKernel

        kernel = AegisKernel()
        # Verify tool is registered in FastMCP
        tools = await kernel.mcp.list_tools()
        assert any(t.name == "apply_rules" for t in tools)

    @pytest.mark.asyncio
    async def test_find_patterns_registration(self):
        from aegis.kernel.server import AegisKernel

        kernel = AegisKernel()
        tools = await kernel.mcp.list_tools()
        assert any(t.name == "find_patterns" for t in tools)

    @pytest.mark.asyncio
    async def test_request_exception_registration(self):
        from aegis.kernel.server import AegisKernel

        kernel = AegisKernel()
        tools = await kernel.mcp.list_tools()
        assert any(t.name == "request_exception" for t in tools)

    @pytest.mark.asyncio
    async def test_get_scorecard_registration(self):
        from aegis.kernel.server import AegisKernel

        kernel = AegisKernel()
        tools = await kernel.mcp.list_tools()
        assert any(t.name == "get_scorecard" for t in tools)
