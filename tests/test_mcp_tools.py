from unittest.mock import MagicMock, patch

import pytest

from aegis.core.models.evolution import EvolutionDecision
from aegis.core.models.governance import EnforcementMode, Rule, Severity
from aegis.kernel.server import AegisKernel


@pytest.fixture
def kernel():
    """Creates an AegisKernel with a mocked container."""
    k = AegisKernel()
    # Replace real container with mock
    mock_container = MagicMock()
    mock_container.workspace_root = "/fake/project"

    # Mock policy parser
    mock_parser = MagicMock()
    mock_container.policy_parser = mock_parser

    # Mock evaluation service
    mock_eval = MagicMock()
    mock_container.evaluation_service = mock_eval

    # Mock baseline manager
    mock_baseline = MagicMock()
    mock_container.baseline_manager = mock_baseline

    # Mock evolution service
    mock_evolution = MagicMock()
    mock_container.evolution_service = mock_evolution

    k.container = mock_container
    return k


class TestMCPTools:
    """
    Test suite for AegisKernel MCP tools.
    """

    @pytest.mark.asyncio
    @patch("aegis.kernel.server.os.path.exists", return_value=True)
    async def test_validate_compliance_clean(self, _mock_exists, kernel):
        kernel.container.evaluation_service.evaluate_workspace.return_value = []
        kernel.container.baseline_manager.is_exempt.return_value = False
        kernel.container.policy_parser.parse_rules.return_value = []

        result = await kernel.validate_architecture_compliance(staged_only=False)
        assert "No new violations" in result

    @pytest.mark.asyncio
    @patch("aegis.kernel.server.os.path.exists", return_value=True)
    async def test_validate_compliance_with_violations(self, _mock_exists, kernel):
        from aegis.domain.evaluation.ports import ArchitecturalViolation

        kernel.container.policy_parser.parse_rules.return_value = [
            Rule(
                id="r1",
                description="desc",
                severity=Severity.HIGH,
                mode=EnforcementMode.BLOCK,
            )
        ]
        kernel.container.evaluation_service.evaluate_workspace.return_value = [
            ArchitecturalViolation(
                file="src/main.py", line=5, rule_id="r1", description="violation"
            )
        ]
        kernel.container.baseline_manager.is_exempt.return_value = False

        result = await kernel.validate_architecture_compliance(staged_only=False)
        assert "ARCHITECTURAL DRIFT" in result
        assert "src/main.py" in result

    @pytest.mark.asyncio
    async def test_apply_remediation_no_violations(self, kernel):
        kernel.container.policy_parser.parse_rules.return_value = []
        kernel.container.evaluation_service.evaluate_workspace.return_value = []
        kernel.container.baseline_manager.is_exempt.return_value = False

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
        kernel.container.policy_parser.parse_rules.return_value = [rule]
        kernel.container.evaluation_service.evaluate_workspace.return_value = [
            ArchitecturalViolation(
                file="src/main.py", line=5, rule_id="r1", description="violation"
            )
        ]
        kernel.container.baseline_manager.is_exempt.return_value = False

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
        kernel.container.policy_parser.parse_rules.return_value = [rule]
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
        kernel.container.policy_parser.parse_rules.return_value = []

        result = await kernel.get_rule_rationale("nonexistent")
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_get_rule_rationale_empty_id(self, kernel):
        result = await kernel.get_rule_rationale("")
        assert "ERROR" in result
        assert "non-empty" in result

    @pytest.mark.asyncio
    async def test_get_rule_rationale_invalid_chars(self, kernel):
        result = await kernel.get_rule_rationale("../etc")
        assert "ERROR" in result
        assert "invalid characters" in result

    @pytest.mark.asyncio
    async def test_get_dependency_graph_empty_name(self, kernel):
        result = await kernel.get_dependency_graph("")
        assert "ERROR" in result
        assert "non-empty" in result

    @pytest.mark.asyncio
    async def test_get_dependency_graph_path_traversal(self, kernel):
        result = await kernel.get_dependency_graph("../secrets")
        assert "ERROR" in result
        assert "not a valid module" in result

    @pytest.mark.asyncio
    async def test_get_dependency_graph_root_path(self, kernel):
        result = await kernel.get_dependency_graph("/etc/passwd")
        assert "ERROR" in result
        assert "not a valid module" in result

    @pytest.mark.asyncio
    @patch("aegis.kernel.server.os.path.exists", return_value=True)
    async def test_validate_compliance_staged(self, _mock_exists, kernel):
        """validate_architecture_compliance with staged_only=True calls evaluate_changes."""
        kernel.container.policy_parser.parse_rules.return_value = []
        kernel.container.evaluation_service.evaluate_changes.return_value = []
        kernel.container.baseline_manager.is_exempt.return_value = False

        result = await kernel.validate_architecture_compliance(staged_only=True)
        assert "No new violations" in result
        kernel.container.evaluation_service.evaluate_changes.assert_called_once()

    @pytest.mark.asyncio
    @patch("aegis.kernel.server.os.path.exists", return_value=True)
    async def test_validate_compliance_full_scan(self, _mock_exists, kernel):
        """validate_architecture_compliance with staged_only=False calls evaluate_workspace."""
        kernel.container.policy_parser.parse_rules.return_value = []
        kernel.container.evaluation_service.evaluate_workspace.return_value = []
        kernel.container.baseline_manager.is_exempt.return_value = False

        result = await kernel.validate_architecture_compliance(staged_only=False)
        assert "No new violations" in result
        kernel.container.evaluation_service.evaluate_workspace.assert_called_once()

    @pytest.mark.asyncio
    @patch("aegis.kernel.server.os.path.exists", return_value=False)
    async def test_validate_compliance_no_rules_yaml(self, _mock_exists, kernel):
        """validate_architecture_compliance returns error when rules.yaml missing."""
        result = await kernel.validate_architecture_compliance()
        assert "not initialized" in result
        kernel.container.policy_parser.parse_rules.return_value = []
        kernel.container.evaluation_service.evaluate_workspace.return_value = []
        kernel.container.baseline_manager.is_exempt.return_value = False
        kernel.container.custom_mcp_tools = []
        kernel.container.loaded_plugins = []

        result = await kernel.server_status()
        assert "Aegis Kernel Status" in result
        assert "/fake/project" in result
        assert "Rules:" in result
        assert "Tools:" in result
