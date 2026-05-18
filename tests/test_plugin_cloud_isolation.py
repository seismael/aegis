import os
import pytest
from aegis.core.container.app import Container
from aegis.domain.policy.models import Rule, Severity, EnforcementMode

class TestCloudIsolationPlugin:
    """Integration test for the CloudIsolationPlugin."""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Setup a temporary workspace with the plugin and a violating file."""
        # 1. Create .aegis/plugins dir
        plugins_dir = tmp_path / ".aegis" / "plugins"
        plugins_dir.mkdir(parents=True)
        
        # 2. Copy the actual plugin into the temp workspace
        plugin_src = os.path.join(os.getcwd(), ".aegis", "plugins", "cloud_isolation.py")
        with open(plugin_src, "r", encoding="utf-8") as f:
            plugin_content = f.read()
        (plugins_dir / "cloud_isolation.py").write_text(plugin_content, encoding="utf-8")
        
        # 3. Create a violating file in the domain
        domain_dir = tmp_path / "src" / "myapp" / "domain"
        domain_dir.mkdir(parents=True)
        (domain_dir / "logic.py").write_text(
            "import boto3\n\ndef process():\n    pass\n", 
            encoding="utf-8"
        )
        
        # 4. Create a non-violating file in infrastructure
        infra_dir = tmp_path / "src" / "myapp" / "infrastructure"
        infra_dir.mkdir(parents=True)
        (infra_dir / "s3_adapter.py").write_text(
            "import boto3\n\nclass S3Adapter:\n    pass\n", 
            encoding="utf-8"
        )
        
        return tmp_path

    def test_plugin_detects_cloud_leak_in_domain(self, workspace):
        # Initialise container for the temp workspace
        container = Container(workspace_root=str(workspace))
        
        # Manually define the rule (normally loaded from YAML)
        rule = Rule(
            id="cloud-isolation-test",
            description="Test cloud isolation",
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
            applies_to=["**/domain/**"],
            metadata={"plugin": "cloud-isolation"}
        )
        
        # Run evaluation
        violations = container.evaluation_service.evaluate_workspace(
            str(workspace), [rule]
        )
        
        # Filter for our specific rule (ScopeFilter is already called in evaluate_workspace)
        relevant = [v for v in violations if v.rule_id == "cloud-isolation-test"]
        
        # Assertions
        assert len(relevant) == 1
        assert "logic.py" in relevant[0].file
        assert "boto3" in relevant[0].description
        
        # Verify infrastructure file is NOT flagged (due to applies_to scope)
        assert not any("s3_adapter.py" in v.file for v in relevant)

    def test_plugin_mcp_tool_registration(self, workspace):
        container = Container(workspace_root=str(workspace))
        
        # Check if the tool is registered in the container
        tools = container.custom_mcp_tools
        tool_names = [t.__name__ for t in tools]
        
        assert "get_cloud_isolation_status" in tool_names
        
        # Call the tool
        status_tool = next(t for t in tools if t.__name__ == "get_cloud_isolation_status")
        status = status_tool()
        
        assert status["status"] == "active"
        assert "boto3" in str(status["default_sdks_monitored"])
