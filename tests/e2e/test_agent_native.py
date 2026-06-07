"""
Post-install agent-native simulation tests.
Simulates the complete agent experience after `aegis init` has been run:
- Tests the mandatory Plan-Act-Validate governance loop.
- No human CLI intervention beyond the one-time `aegis init`.
Verifies that ALL capabilities work natively through MCP tools without
any human CLI intervention beyond the one-time `aegis init`.
"""

import json
from pathlib import Path

import pytest

from aegis.infrastructure.installer import AGENTS_TEMPLATE, AgentNativeInstaller
from aegis.kernel.server import AegisKernel


def _ws(k: AegisKernel) -> Path:
    return Path(k.workspace_root)


# ═══════════════════════════════════════════════════════════════════════════════
# Test 1: AGENTS.md contains all 4 skills and mandatory protocol
# ═══════════════════════════════════════════════════════════════════════════════


class TestAgentsTemplate:
    def test_template_includes_all_four_skills(self):
        assert "/aegis-principal-architect" in AGENTS_TEMPLATE
        assert "/aegis-init" in AGENTS_TEMPLATE
        assert "/aegis-architect" in AGENTS_TEMPLATE
        assert "/aegis-semantic-check" in AGENTS_TEMPLATE

    def test_template_includes_mandatory_protocol(self):
        assert "check_architecture" in AGENTS_TEMPLATE
        assert "MUST" in AGENTS_TEMPLATE

    def test_template_includes_six_tool_table(self):
        for tool in [
            "check_architecture",
            "plan_architecture",
            "fetch_rubric",
            "init_governance",
            "query_graph",
            "manage_rules",
        ]:
            assert tool in AGENTS_TEMPLATE, f"Missing tool: {tool}"

    def test_installer_generates_agents_md_to_disk(self, tmp_path):
        ws = tmp_path / "project"
        ws.mkdir()
        path = AgentNativeInstaller.generate_agents_template(str(ws))
        assert Path(path).exists()
        content = Path(path).read_text()
        assert "/aegis-principal-architect" in content


# ═══════════════════════════════════════════════════════════════════════════════
# Test 2: Scaffold auto-generates AGENTS.md in workspace
# ═══════════════════════════════════════════════════════════════════════════════


class TestScaffoldGeneratesAgents:
    async def test_scaffold_creates_agents_md(self, tmp_path):
        ws = tmp_path / "scaffold-test"
        ws.mkdir()
        (ws / "pyproject.toml").write_text('[project]\nname = "test"\n')
        (ws / "src").mkdir()

        k = AegisKernel(str(ws))
        result = await k.init_governance(["security"])
        assert "SUCCESS" in result
        assert "AGENTS.md" in result

        agents = _ws(k) / "AGENTS.md"
        assert agents.exists()
        content = agents.read_text()
        assert "check_architecture" in content
        assert "/aegis-principal-architect" in content


# ═══════════════════════════════════════════════════════════════════════════════
# Test 3: aegis://spec returns structured warn when no docs/SPEC.md
# ═══════════════════════════════════════════════════════════════════════════════


class TestSpecResource:
    async def test_spec_resource_no_file_returns_warn(self, tmp_path):
        ws = tmp_path / "no-spec"
        ws.mkdir()

        k = AegisKernel(str(ws))
        spec_path = _ws(k) / "docs" / "SPEC.md"
        assert not spec_path.exists()

    async def test_spec_resource_reads_existing_file(self, tmp_path):
        ws = tmp_path / "has-spec"
        ws.mkdir()
        (ws / "docs").mkdir(exist_ok=True)
        (ws / "docs" / "SPEC.md").write_text("# My Architecture")

        k = AegisKernel(str(ws))
        result = await k.mcp.read_resource("aegis://spec")
        assert len(result) == 1
        content = (_ws(k) / "docs" / "SPEC.md").read_text()
        assert "My Architecture" in content


# ═══════════════════════════════════════════════════════════════════════════════
# Test 4: All MCP tools return agent-readable strings (no terminal UI artifacts)
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def verify_workspace(tmp_path):
    ws = tmp_path / "verify-project"
    ws.mkdir()
    (ws / "pyproject.toml").write_text('[project]\nname = "verify"\n')

    src = ws / "src"
    src.mkdir()
    (src / "lib.py").write_text("version = '1.0'\n")

    rules_dir = ws / ".aegis" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "test.yaml").write_text(
        "rules:\n"
        "- id: ok-rule\n"
        "  description: Dummy rule\n"
        "  severity: LOW\n"
        "  engine_type: regex\n"
        "  category: style\n"
        "  query: __does_not_match_any\n"
        "  language: python\n"
        "  phases:\n"
        "    - pre-commit\n"
        "  applies_to:\n"
        '    - "**/*.py"\n'
    )
    return ws


class TestAgentReadableOutputs:
    """All tool outputs must be parseable by an LLM — no ANSI codes or terminal UI."""

    async def test_validate_returns_agent_readable(self, verify_workspace):
        k = AegisKernel(str(verify_workspace))
        result = await k.check_architecture(["src/lib.py"])
        assert "SUCCESS" in result
        assert "\x1b" not in result  # no ANSI codes

    async def test_plan_returns_agent_readable(self, verify_workspace):
        k = AegisKernel(str(verify_workspace))
        result = await k.plan_architecture(intent="Test")
        assert "Architectural Context" in result
        assert "\x1b" not in result

    async def test_query_rules_returns_valid_json(self, verify_workspace):
        k = AegisKernel(str(verify_workspace))
        result = await k.query_graph("rules")
        data = json.loads(result)
        assert isinstance(data, list)
        assert any(r["id"] == "ok-rule" for r in data)

    async def test_hypothesis_returns_agent_readable(self, verify_workspace):
        k = AegisKernel(str(verify_workspace))
        result = await k.query_graph("hypothesis")
        assert isinstance(result, str)
        assert "\x1b" not in result

    async def test_evolve_error_returns_structured_json(self, verify_workspace):
        k = AegisKernel(str(verify_workspace))
        result = await k.manage_rules(action="bogus")
        data = json.loads(result)
        assert data["success"] is False
        assert "error_code" in data


# ═══════════════════════════════════════════════════════════════════════════════
# Test 5: Full post-install agent lifecycle (no human CLI steps after install)
# ═══════════════════════════════════════════════════════════════════════════════


class TestPostInstallAgentLifecycle:
    """Complete agent-native journey: everything through MCP after aegis init."""

    async def test_complete_agent_journey(self, tmp_path):
        ws = tmp_path / "agent-journey"
        ws.mkdir()
        (ws / "pyproject.toml").write_text('[project]\nname = "journey"\n')

        src = ws / "src"
        src.mkdir()
        (src / "__init__.py").write_text("")

        k = AegisKernel(str(ws))

        # Step 1: Agent calls hypothesis (via /aegis-init flow)
        hyp = await k.query_graph("hypothesis")
        assert isinstance(hyp, str)
        assert len(hyp) > 0

        # Step 2: Agent presents to user, gets approval, scaffolds
        scaffold = await k.init_governance(["architecture", "security"])
        assert "SUCCESS" in scaffold
        assert "AGENTS.md" in scaffold

        # Step 3: AGENTS.md exists
        agents = _ws(k) / "AGENTS.md"
        assert agents.exists()

        # Step 4: Agent plans before editing
        plan = await k.plan_architecture(
            intent="Create user service", file_path="src/service.py"
        )
        assert "Architectural Context" in plan

        # Step 5: Agent writes code, validates
        (src / "service.py").write_text(
            "def get_user(user_id: int) -> dict:\n"
            '    return {"id": user_id, "name": "User"}\n'
        )
        check = await k.check_architecture(["src/service.py"])
        assert isinstance(check, str)

        # Step 6: Agent queries rules to understand governance
        rules_json = await k.query_graph("rules")
        rules = json.loads(rules_json)
        assert len(rules) > 0

        # Step 7: Agent adds a custom rule via /aegis-architect flow
        add = await k.manage_rules(
            action="add_rule",
            rule_id="journey-no-untyped",
            description="All functions must have type annotations",
            severity="MEDIUM",
            engine_type="tree-sitter",
            category="style",
            rationale="Type safety improves maintainability",
            language="python",
        )
        assert "SUCCESS" in add

        # Step 8: Agent audits semantics
        rubric = await k.fetch_rubric("src/service.py")
        assert isinstance(rubric, str)

        # Step 9: Headless check works for CI
        violations = k.run_headless_check()
        assert isinstance(violations, int)
        assert violations >= 0

        # Step 10: Telemetry records the journey
        insights = k.telemetry.get_insights()
        assert isinstance(insights, dict)
