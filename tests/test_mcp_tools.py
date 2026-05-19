from unittest.mock import MagicMock

import pytest

from aegis.core.models.evolution import EvolutionDecision
from aegis.domain.policy.models import EnforcementMode, Rule, Severity
from aegis.kernel.server import AegisKernel


@pytest.fixture
def kernel():
    """Creates an AegisKernel with a mocked container."""
    k = AegisKernel()
    # Replace real container with mock
    mock_container = MagicMock()
    mock_container.workspace_root = "/fake/project"

    # Default: no rules loaded (tests override per-test)
    mock_container.load_rules.return_value = []

    # Mock evaluation service
    mock_eval = MagicMock()
    mock_container.evaluation_service = mock_eval

    # Mock baseline manager
    mock_baseline = MagicMock()
    mock_container.baseline_manager = mock_baseline

    # Mock evolution service
    mock_evolution = MagicMock()
    mock_container.evolution_service = mock_evolution

    # Mock governance service
    mock_governance = MagicMock()
    mock_governance.get_active_violations.return_value = []
    mock_container.governance_service = mock_governance

    k.container = mock_container
    return k


class TestMCPTools:
    """
    Test suite for AegisKernel MCP tools.
    """

    @pytest.mark.asyncio
    async def test_validate_compliance_clean(self, kernel):
        kernel.container.load_rules.return_value = [Rule(id="r1", description="desc")]
        result = await kernel.validate_architecture_compliance(staged_only=False)
        assert "No new violations" in result

    @pytest.mark.asyncio
    async def test_validate_compliance_with_violations(self, kernel):
        from aegis.domain.evaluation.ports import ArchitecturalViolation

        kernel.container.load_rules.return_value = [
            Rule(
                id="r1",
                description="desc",
                severity=Severity.HIGH,
                mode=EnforcementMode.BLOCK,
            )
        ]
        kernel.container.governance_service.get_active_violations.return_value = [
            ArchitecturalViolation(
                file="src/main.py", line=5, rule_id="r1", description="violation"
            )
        ]

        result = await kernel.validate_architecture_compliance(staged_only=False)
        assert "ARCHITECTURAL DRIFT" in result
        assert "src/main.py" in result

    @pytest.mark.asyncio
    async def test_apply_remediation_no_violations(self, kernel):
        kernel.container.load_rules.return_value = []

        result = await kernel.apply_architectural_remediation()
        assert "No remediation needed" in result

    @pytest.mark.asyncio
    async def test_apply_remediation_with_violations(self, kernel):
        from aegis.domain.evaluation.ports import ArchitecturalViolation

        rule = Rule(
            id="r1",
            description="desc",
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
        )
        kernel.container.load_rules.return_value = [rule]
        kernel.container.governance_service.get_active_violations.return_value = [
            ArchitecturalViolation(
                file="src/main.py", line=5, rule_id="r1", description="violation"
            )
        ]

        result = await kernel.apply_architectural_remediation()
        assert "INTERVENTION" in result
        assert "src/main.py" in result

    @pytest.mark.asyncio
    async def test_get_rule_rationale_found(self, kernel):
        rule = Rule(
            id="r1",
            description="desc",
            severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK,
            rationale="Keep architecture clean.",
        )
        kernel.container.load_rules.return_value = [rule]
        kernel.container.evolution_service.load_log.return_value = MagicMock(
            decisions=[
                EvolutionDecision(
                    rule_id="r1",
                    action="suppress",
                    rationale="Approved for hotfix.",
                )
            ]
        )

        result = await kernel.get_rule_rationale("r1")
        assert "r1" in result
        assert "Keep architecture clean." in result
        assert "suppress" in result

    @pytest.mark.asyncio
    async def test_get_rule_rationale_not_found(self, kernel):
        kernel.container.load_rules.return_value = []

        result = await kernel.get_rule_rationale("nonexistent")
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_get_rule_rationale_empty_id(self, kernel):
        result = await kernel.get_rule_rationale("")
        assert "INVALID_INPUT" in result

    @pytest.mark.asyncio
    async def test_get_rule_rationale_invalid_chars(self, kernel):
        result = await kernel.get_rule_rationale("../etc")
        assert "INVALID_INPUT" in result
        assert "invalid characters" in result

    @pytest.mark.asyncio
    async def test_get_dependency_graph_empty_name(self, kernel):
        result = await kernel.get_dependency_graph("")
        assert "INVALID_INPUT" in result

    @pytest.mark.asyncio
    async def test_get_dependency_graph_path_traversal(self, kernel):
        result = await kernel.get_dependency_graph("../secrets")
        assert "INVALID_INPUT" in result
        assert "not a valid module" in result

    @pytest.mark.asyncio
    async def test_get_dependency_graph_root_path(self, kernel):
        result = await kernel.get_dependency_graph("/etc/passwd")
        assert "INVALID_INPUT" in result
        assert "not a valid module" in result

    @pytest.mark.asyncio
    async def test_validate_compliance_staged(self, kernel):
        """validate_architecture_compliance staged_only=True uses evaluate_changes."""
        kernel.container.load_rules.return_value = [Rule(id="r1", description="desc")]
        kernel.container.evaluation_service.evaluate_changes.return_value = []
        kernel.container.baseline_manager.is_exempt.return_value = False

        result = await kernel.validate_architecture_compliance(staged_only=True)
        assert "No new violations" in result
        kernel.container.evaluation_service.evaluate_changes.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_compliance_full_scan(self, kernel):
        """validate_architecture_compliance full scan calls governance_service."""
        kernel.container.load_rules.return_value = [Rule(id="r1", description="desc")]

        result = await kernel.validate_architecture_compliance(staged_only=False)
        assert "No new violations" in result
        kernel.container.governance_service.get_active_violations.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_compliance_no_rules(self, kernel):
        """validate_architecture_compliance returns error when no rules loaded."""
        kernel.container.load_rules.return_value = []
        kernel.container.evaluation_service.evaluate_workspace.return_value = []
        kernel.container.baseline_manager.is_exempt.return_value = False
        kernel.container.custom_mcp_tools = []
        kernel.container.loaded_plugins = []

        result = await kernel.validate_architecture_compliance()
        assert "not initialized" in result

        result = await kernel.server_status()
        assert "Aegis Kernel Status" in result
        assert "/fake/project" in result
        assert "Rules:" in result
        assert "Tools:" in result


class TestCORSSupport:
    """Tests for CORS middleware on SSE/HTTP transport."""

    def test_run_signature_includes_cors(self):
        """run() method accepts cors_origins parameter."""
        import inspect

        from aegis.kernel.server import AegisKernel

        sig = inspect.signature(AegisKernel.run)
        assert "cors_origins" in sig.parameters

    def test_cors_parsing(self):
        """Comma-separated cors_origins splits correctly."""
        from unittest.mock import MagicMock

        from starlette.middleware.cors import CORSMiddleware

        # Simulate the parsing in run()
        raw = "http://localhost:3000,https://app.example.com"
        origins = [o.strip() for o in raw.split(",")]
        assert origins == ["http://localhost:3000", "https://app.example.com"]

        # Verify it creates valid middleware kwargs
        mw_kwargs = {
            "allow_origins": origins,
            "allow_methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["*"],
        }
        mock_app = MagicMock()
        mw = CORSMiddleware(mock_app, **mw_kwargs)
        # CORSMiddleware stores origins
        assert mw.allow_origins == origins
