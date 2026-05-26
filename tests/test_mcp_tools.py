"""Integration tests for MCP tool surface of AegisKernel."""

from pathlib import Path

import pytest

from aegis.kernel.server import AegisKernel


def _ws(k: AegisKernel) -> Path:
    return Path(k.workspace_root)


@pytest.fixture
def kernel(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    rules_dir = workspace / ".aegis" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "test.yaml").write_text(
        "rules:\n"
        "- id: test-no-print\n"
        "  description: No print statements\n"
        "  severity: HIGH\n"
        "  engine_type: regex\n"
        "  category: style\n"
        "  query: print\n"
        "  language: python\n"
        "  phases:\n"
        "    - pre-commit\n"
        "  applies_to:\n"
        '    - "**/*.py"\n'
    )
    src = workspace / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "module.py").write_text('print("hello world")\n')
    return AegisKernel(str(workspace))


class TestValidateArchitectureCompliance:
    async def test_violations_detected(self, kernel):
        result = await kernel.validate_architecture_compliance(["src/module.py"])
        assert "test-no-print" in result or "violation" in result.lower()

    async def test_no_violations_returns_success(self, kernel):
        (_ws(kernel) / "src" / "module.py").write_text("x = 1\n")
        result = await kernel.validate_architecture_compliance(["src/module.py"])
        assert "SUCCESS" in result


class TestRequestSemanticGradingRubric:
    async def test_no_semantic_rules_returns_clear_message(self, kernel):
        result = await kernel.request_semantic_grading_rubric("src/module.py")
        assert "NO_SEMANTIC_RULES" in result

    async def test_returns_rubric_for_target_file(self, kernel):
        rules_dir = _ws(kernel) / ".aegis" / "rules"
        (rules_dir / "semantic.yaml").write_text(
            "rules:\n"
            "- id: sem-naming\n"
            "  description: Variables must use domain language\n"
            "  severity: LOW\n"
            "  engine_type: semantic\n"
            "  category: semantic\n"
            "  language: python\n"
            "  applies_to:\n"
            '    - "**/*.py"\n'
        )
        result = await kernel.request_semantic_grading_rubric("src/module.py")
        assert "Grading Rubric" in result
        assert "sem-naming" in result


class TestScaffoldGovernanceFramework:
    async def test_scaffold_invalid_pack(self, kernel):
        result = await kernel.scaffold_governance_framework(["nonexistent-pack"])
        assert "SCAFFOLD_FAILED" in result

    async def test_scaffold_valid_pack(self, kernel):
        result = await kernel.scaffold_governance_framework(["security"])
        assert "SUCCESS" in result
        assert "security" in result


class TestQueryKnowledgeGraph:
    async def test_hypothesis(self, kernel):
        result = await kernel.query_knowledge_graph("hypothesis")
        assert "Detected" in result or "Proposed" in result

    async def test_rules_list(self, kernel):
        result = await kernel.query_knowledge_graph("rules")
        assert "test-no-print" in result


class TestEvolveRuleset:
    async def test_add_rule_creates_custom_yaml(self, kernel):
        result = await kernel.evolve_ruleset(
            action="add_rule",
            rule_id="custom-hello",
            description="No hello allowed",
            severity="MEDIUM",
            engine_type="regex",
            category="style",
            regex_pattern="hello",
        )
        assert "SUCCESS" in result
        assert "custom-hello" in result

        custom = _ws(kernel) / ".aegis" / "rules" / "custom.yaml"
        assert custom.exists()
        content = custom.read_text()
        assert "custom-hello" in content

    async def test_add_rule_duplicate_rejected(self, kernel):
        await kernel.evolve_ruleset(
            action="add_rule",
            rule_id="dup-rule",
            description="First",
            severity="LOW",
            engine_type="regex",
            category="style",
            regex_pattern="x",
        )
        result = await kernel.evolve_ruleset(
            action="add_rule",
            rule_id="dup-rule",
            description="Second",
            severity="LOW",
            engine_type="regex",
            category="style",
            regex_pattern="y",
        )
        assert "DUPLICATE_RULE" in result

    async def test_unknown_action(self, kernel):
        result = await kernel.evolve_ruleset(action="bogus_action")
        assert "INVALID_INPUT" in result


class TestPlanArchitecture:
    async def test_plan_with_intent_only(self, kernel):
        result = await kernel.plan_architecture(intent="Add new feature")
        assert "Architectural Context" in result

    async def test_plan_with_file_path(self, kernel):
        result = await kernel.plan_architecture(
            intent="Edit module", file_path="src/module.py"
        )
        assert "Architectural Context" in result

    async def test_plan_with_code_string(self, kernel):
        result = await kernel.plan_architecture(
            intent="Check snippet",
            code_string='print("test")\n',
            language="python",
        )
        assert "Architectural Context" in result

    async def test_plan_with_violating_code(self, kernel):
        result = await kernel.plan_architecture(
            intent="Validate snippet",
            code_string='print("bad")\n',
            language="python",
            file_path="src/test.py",
        )
        assert "Code Violations" in result
        assert "test-no-print" in result


class TestRunHeadlessCheck:
    def test_headless_check_finds_violations(self, kernel):
        violations = kernel.run_headless_check()
        assert violations > 0
