from unittest.mock import MagicMock, patch

import pytest

from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.policy.models import EngineType, Rule, Severity
from aegis.kernel.server import AegisKernel


@pytest.fixture
def kernel(tmp_path):
    with patch("aegis.kernel.server.PolicyParser"):
        k = AegisKernel(workspace_root=str(tmp_path))
        # Mock evaluation service
        k.evaluation = MagicMock()
        return k


@pytest.mark.asyncio
async def test_get_context_resource(kernel, tmp_path):
    # Setup mock rules
    rule1 = Rule(
        id="RULE1",
        description="Critical Rule",
        severity=Severity.CRITICAL,
        engine_type=EngineType.REGEX,
    )
    rule2 = Rule(
        id="RULE2",
        description="High Rule",
        severity=Severity.HIGH,
        engine_type=EngineType.REGEX,
    )
    rule3 = Rule(
        id="RULE3",
        description="Medium Rule",
        severity=Severity.MEDIUM,
        engine_type=EngineType.REGEX,
    )
    rule4 = Rule(
        id="RULE4",
        description="Low Rule",
        severity=Severity.LOW,
        engine_type=EngineType.REGEX,
    )

    kernel._load_rules = MagicMock(return_value=[rule1, rule2, rule3, rule4])

    # Create a dummy file
    test_file = tmp_path / "test.py"
    test_file.write_text("print('hello')")

    # Mock evaluation to return 1 violation out of 4 rules -> 75% health
    kernel.evaluation.evaluate_file.return_value = [
        ArchitecturalViolation(
            file="test.py", line=1, rule_id="RULE1", description="Violation"
        )
    ]

    # Call resource
    resources = await kernel.mcp.read_resource("aegis://context/test.py")
    content = resources[0].content

    assert "Aegis Law Summary for: `test.py`" in content
    assert "Module Health: 75%" in content
    assert "RULE1" in content
    assert "RULE2" in content
    assert "RULE3" in content
    assert "RULE4" not in content  # Only top 3
    scorecard_link = (
        "[View full AEGIS.md scorecard](file:///"
        + str(tmp_path / ".aegis" / "AEGIS.md").replace("\\", "/")
        + ")"
    )
    assert scorecard_link in content


@pytest.mark.asyncio
async def test_get_scorecard_resource_not_found(kernel):
    resources = await kernel.mcp.read_resource("aegis://scorecard")
    content = resources[0].content
    assert "AEGIS.md not found" in content


@pytest.mark.asyncio
async def test_get_scorecard_resource_found(kernel, tmp_path):
    aegis_dir = tmp_path / ".aegis"
    aegis_dir.mkdir(exist_ok=True)
    scorecard_file = aegis_dir / "AEGIS.md"
    scorecard_content = "# Project Health\nScore: 100%"
    scorecard_file.write_text(scorecard_content)

    resources = await kernel.mcp.read_resource("aegis://scorecard")
    content = resources[0].content
    assert scorecard_content in content
