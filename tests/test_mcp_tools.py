from unittest.mock import MagicMock

import pytest

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
        import json

        kernel.container.load_rules.return_value = [Rule(id="r1", description="desc")]
        raw = await kernel._validate_architecture_compliance(staged_only=False)
        result = json.loads(raw)
        assert result["passed"] is True
        assert result["total_violations"] == 0

    @pytest.mark.asyncio
    async def test_validate_compliance_with_violations(self, kernel):
        import json

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

        raw = await kernel._validate_architecture_compliance(staged_only=False)
        result = json.loads(raw)
        assert result["passed"] is False
        assert result["total_violations"] == 1
        assert result["violations"][0]["file"] == "src/main.py"

    @pytest.mark.asyncio
    async def test_apply_remediation_no_violations(self, kernel):
        kernel.container.load_rules.return_value = []

        result = await kernel._apply_architectural_remediation()
        assert "No remediation needed" in result.handoff_prompt

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

        result = await kernel._apply_architectural_remediation()
        assert "INTERVENTION" in result.handoff_prompt
        assert "src/main.py" in result.handoff_prompt

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
                {
                    "rule_id": "r1",
                    "action": "suppress",
                    "rationale": "Approved for hotfix.",
                }
            ]
        )

        result = await kernel._get_rule_rationale("r1")
        assert "r1" in result
        assert "Keep architecture clean." in result
        assert "suppress" in result

    @pytest.mark.asyncio
    async def test_get_rule_rationale_not_found(self, kernel):
        kernel.container.load_rules.return_value = []

        result = await kernel._get_rule_rationale("nonexistent")
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_get_rule_rationale_empty_id(self, kernel):
        result = await kernel._get_rule_rationale("")
        assert "INVALID_INPUT" in result

    @pytest.mark.asyncio
    async def test_get_rule_rationale_invalid_chars(self, kernel):
        result = await kernel._get_rule_rationale("../etc")
        assert "INVALID_INPUT" in result
        assert "invalid characters" in result

    @pytest.mark.asyncio
    async def test_get_dependency_graph_empty_name(self, kernel):
        result = await kernel._get_dependency_graph("")
        assert "INVALID_INPUT" in result

    @pytest.mark.asyncio
    async def test_get_dependency_graph_path_traversal(self, kernel):
        result = await kernel._get_dependency_graph("../secrets")
        assert "INVALID_INPUT" in result
        assert "not a valid module" in result

    @pytest.mark.asyncio
    async def test_get_dependency_graph_root_path(self, kernel):
        result = await kernel._get_dependency_graph("/etc/passwd")
        assert "INVALID_INPUT" in result
        assert "not a valid module" in result

    @pytest.mark.asyncio
    async def test_validate_compliance_staged(self, kernel):
        """validate_architecture_compliance staged_only=True uses evaluate_changes."""
        import json

        kernel.container.load_rules.return_value = [Rule(id="r1", description="desc")]
        kernel.container.evaluation_service.evaluate_changes.return_value = []
        kernel.container.baseline_manager.is_exempt.return_value = False

        raw = await kernel._validate_architecture_compliance(staged_only=True)
        result = json.loads(raw)
        assert result["passed"] is True
        kernel.container.evaluation_service.evaluate_changes.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_compliance_full_scan(self, kernel):
        """validate_architecture_compliance full scan calls governance_service."""
        import json

        kernel.container.load_rules.return_value = [Rule(id="r1", description="desc")]

        raw = await kernel._validate_architecture_compliance(staged_only=False)
        result = json.loads(raw)
        assert result["passed"] is True
        kernel.container.governance_service.get_active_violations.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_compliance_no_rules(self, kernel):
        """validate_architecture_compliance returns error when no rules loaded."""
        import json

        kernel.container.load_rules.return_value = []
        kernel.container.evaluation_service.evaluate_workspace.return_value = []
        kernel.container.baseline_manager.is_exempt.return_value = False
        kernel.container.custom_mcp_tools = []
        kernel.container.loaded_plugins = []

        result = await kernel._validate_architecture_compliance()
        assert "not initialized" in result

        result = json.loads(await kernel._server_status())
        assert result["status"] in ("ready", "degraded")
        assert result["workspace"] == "/fake/project"

    @pytest.mark.asyncio
    async def test_get_active_context(self, kernel):
        """get_active_context returns matching rules for a file."""
        import json

        kernel.container.load_rules.return_value = [
            Rule(id="r1", description="core rule", language="py"),
            Rule(id="r2", description="test rule", language="py"),
        ]
        kernel.container.graph_analyzer = MagicMock()
        kernel.container.graph_analyzer.build_import_graph.return_value = ({}, {})

        result = json.loads(await kernel._get_active_context("src/core/main.py"))
        assert result["total_rules"] == 2
        rule_ids = {r["id"] for r in result["rules"]}
        assert "r1" in rule_ids
        assert "r2" in rule_ids

    @pytest.mark.asyncio
    async def test_get_active_context_no_rules(self, kernel):
        """get_active_context returns message when no rules loaded."""
        import json

        kernel.container.load_rules.return_value = []

        result = json.loads(await kernel._get_active_context("src/main.py"))
        assert result["total_rules"] == 0

    @pytest.mark.asyncio
    async def test_get_active_context_uninitialized(self, kernel):
        """get_active_context returns error when container is None."""
        kernel.container = None

        result = await kernel._get_active_context("src/main.py")
        assert "CONTAINER_NOT_INIT" in result

    @pytest.mark.asyncio
    async def test_evaluate_code_delta_ok(self, kernel):
        """evaluate_code_delta returns passed=true for clean code."""
        import json

        kernel.container.load_rules.return_value = [
            Rule(id="r1", description="test", language="py"),
        ]
        kernel.container.evaluation_service.evaluate_code_string.return_value = []

        result = json.loads(await kernel._evaluate_code_delta("def f(): pass", "py"))
        assert result["passed"] is True
        assert result["total_violations"] == 0

    @pytest.mark.asyncio
    async def test_evaluate_code_delta_with_violations(self, kernel):
        """evaluate_code_delta returns violations in structured JSON."""
        import json

        from aegis.domain.evaluation.ports import ArchitecturalViolation

        kernel.container.load_rules.return_value = [
            Rule(id="r1", description="test", language="py"),
        ]
        kernel.container.evaluation_service.evaluate_code_string.return_value = [
            ArchitecturalViolation(
                file="memory.py",
                line=1,
                rule_id="r1",
                description="no print",
                severity="HIGH",
            )
        ]

        result = json.loads(await kernel._evaluate_code_delta("print('x')", "py"))
        assert result["passed"] is False
        assert result["violations"][0]["rule_id"] == "r1"
        assert result["violations"][0]["description"] == "no print"

    @pytest.mark.asyncio
    async def test_evaluate_code_delta_empty_string(self, kernel):
        """evaluate_code_delta returns INVALID_INPUT for empty code."""
        result = await kernel._evaluate_code_delta("", "py")
        assert "INVALID_INPUT" in result

    @pytest.mark.asyncio
    async def test_evaluate_code_delta_empty_language(self, kernel):
        """evaluate_code_delta returns INVALID_INPUT for empty language."""
        result = await kernel._evaluate_code_delta("def f(): pass", "")
        assert "INVALID_INPUT" in result

    @pytest.mark.asyncio
    async def test_evaluate_code_delta_no_rules(self, kernel):
        """evaluate_code_delta returns NOT_INITIALIZED when no rules."""
        kernel.container.load_rules.return_value = []

        result = await kernel._evaluate_code_delta("def f(): pass", "py")
        assert "NOT_INITIALIZED" in result

    @pytest.mark.asyncio
    async def test_evaluate_code_delta_service_unavailable(self, kernel):
        """evaluate_code_delta returns SERVICE_UNAVAILABLE when eval service None."""
        kernel.container.load_rules.return_value = [
            Rule(id="r1", description="test", language="py"),
        ]
        kernel.container.evaluation_service = None

        result = await kernel._evaluate_code_delta("def f(): pass", "py")
        assert "SERVICE_UNAVAILABLE" in result

    @pytest.mark.asyncio
    async def test_get_active_context_graph_failure(self, kernel):
        """get_active_context degrades gracefully when build_import_graph fails."""
        import json

        kernel.container.load_rules.return_value = [
            Rule(id="r1", description="core rule", language="py"),
        ]
        kernel.container.graph_analyzer = MagicMock()
        kernel.container.graph_analyzer.build_import_graph.side_effect = RuntimeError(
            "fail"
        )

        result = json.loads(await kernel._get_active_context("src/core/main.py"))
        assert result["total_rules"] == 1
        assert result["rules"][0]["id"] == "r1"


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
