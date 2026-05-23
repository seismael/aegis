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
