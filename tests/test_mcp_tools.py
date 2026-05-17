import pytest
from unittest.mock import MagicMock, patch
from aegis.kernel.server import AegisKernel
from aegis.core.models.governance import Rule, Severity, EnforcementMode
from aegis.core.models.evolution import EvolutionDecision


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
    async def test_validate_compliance_clean(self, mock_exists, kernel):
        kernel.container.evaluation_service.evaluate_workspace.return_value = []
        kernel.container.baseline_manager.is_exempt.return_value = False
        kernel.container.policy_parser.parse_rules.return_value = []

        result = await kernel.validate_architecture_compliance(staged_only=False)
        assert "No NEW violations" in result

    @pytest.mark.asyncio
    @patch("aegis.kernel.server.os.path.exists", return_value=True)
    async def test_validate_compliance_with_violations(self, mock_exists, kernel):
        from aegis.domain.evaluation.ports import ASTViolation

        kernel.container.policy_parser.parse_rules.return_value = [
            Rule(id="r1", description="desc", severity=Severity.HIGH, mode=EnforcementMode.BLOCK)
        ]
        kernel.container.evaluation_service.evaluate_workspace.return_value = [
            ASTViolation(file="src/main.py", line=5, rule_id="r1", description="violation")
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
        from aegis.domain.evaluation.ports import ASTViolation

        rule = Rule(id="r1", description="desc", severity=Severity.HIGH, mode=EnforcementMode.BLOCK)
        kernel.container.policy_parser.parse_rules.return_value = [rule]
        kernel.container.evaluation_service.evaluate_workspace.return_value = [
            ASTViolation(file="src/main.py", line=5, rule_id="r1", description="violation")
        ]
        kernel.container.baseline_manager.is_exempt.return_value = False

        result = await kernel.apply_architectural_remediation()
        assert "INTERVENTION" in result
        assert "src/main.py" in result

    @pytest.mark.asyncio
    async def test_get_rule_rationale_found(self, kernel):
        rule = Rule(
            id="r1", description="desc", severity=Severity.HIGH,
            mode=EnforcementMode.BLOCK, rationale="Keep architecture clean.",
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
