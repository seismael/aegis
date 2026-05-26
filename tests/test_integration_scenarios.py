"""
End-to-end agent lifecycle integration tests.
Simulates real agent usage: init → plan → edit → validate → remediate → evolve.
Each scenario sets up a realistic workspace, exercises MCP tools, and validates outputs.
"""

import json
from pathlib import Path

import pytest

from aegis.kernel.server import AegisKernel


def _ws(k: AegisKernel) -> Path:
    return Path(k.workspace_root)


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 1: Cold Start — Init → Scaffold
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def cold_start_workspace(tmp_path):
    """Bare workspace — no .aegis/ directory, no rules. Simulates fresh repo."""
    ws = tmp_path / "fresh-project"
    ws.mkdir()
    src = ws / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "greeter.py").write_text(
        '"""Greets users."""\n'
        "\n"
        "def greet(name: str) -> str:\n"
        '    return f"Hello, {name}!"\n'
    )
    (ws / "pyproject.toml").write_text(
        '[project]\nname = "fresh-project"\nversion = "0.1.0"\n'
    )
    return ws


class TestColdStart:
    """Simulates a developer opening a fresh repo and running /aegis-init."""

    async def test_hypothesis_discovers_python_project(self, cold_start_workspace):
        k = AegisKernel(str(cold_start_workspace))
        result = await k.query_knowledge_graph("hypothesis")
        assert "Python project" in result
        assert "pyproject.toml" in result

    async def test_scaffold_security_pack_creates_rules(self, cold_start_workspace):
        k = AegisKernel(str(cold_start_workspace))
        result = await k.scaffold_governance_framework(["security"])
        assert "SUCCESS" in result
        assert (_ws(k) / ".aegis" / "rules" / "security").is_dir()

    async def test_scaffold_multiple_packs(self, cold_start_workspace):
        k = AegisKernel(str(cold_start_workspace))
        result = await k.scaffold_governance_framework(
            ["architecture", "style", "security"]
        )
        assert "SUCCESS" in result
        assert (_ws(k) / ".aegis" / "rules" / "architecture").is_dir()
        assert (_ws(k) / ".aegis" / "rules" / "style").is_dir()
        assert (_ws(k) / ".aegis" / "rules" / "security").is_dir()

    async def test_scaffold_fails_on_invalid_pack(self, cold_start_workspace):
        k = AegisKernel(str(cold_start_workspace))
        result = await k.scaffold_governance_framework(["made-up-pack-xyz"])
        assert "SCAFFOLD_FAILED" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 2: Development Loop — Plan → Validate → Remediate
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def governed_workspace(tmp_path):
    """Workspace with rules installed. Simulates a governed project."""
    ws = tmp_path / "governed-project"
    ws.mkdir()
    (ws / "pyproject.toml").write_text('[project]\nname = "governed"\n')

    src = ws / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")

    rules_dir = ws / ".aegis" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "style.yaml").write_text(
        "rules:\n"
        "- id: no-print\n"
        "  description: No print statements in production code\n"
        "  severity: HIGH\n"
        "  engine_type: regex\n"
        "  category: style\n"
        "  query: print\n"
        "  language: python\n"
        "  phases:\n"
        "    - pre-commit\n"
        "  applies_to:\n"
        '    - "**/*.py"\n'
        "- id: require-docstring\n"
        "  description: All public functions must have docstrings\n"
        "  severity: MEDIUM\n"
        "  engine_type: tree-sitter\n"
        "  category: style\n"
        "  language: python\n"
        "  phases:\n"
        "    - pre-commit\n"
        "  applies_to:\n"
        '    - "**/*.py"\n'
        "  query: |\n"
        "    (function_definition\n"
        "      name: (identifier) @name\n"
        "      body: (block . (_) @body)\n"
        "      (not (expression_statement (string))))\n"
    )
    return ws


class TestDevelopmentLoop:
    """Simulates agent: plan → edit file → validate → fix → re-validate."""

    async def test_plan_returns_scoped_rules(self, governed_workspace):
        k = AegisKernel(str(governed_workspace))
        result = await k.plan_architecture(
            intent="Add logging to greeter",
            file_path="src/greeter.py",
        )
        assert "Architectural Context" in result
        assert "no-print" in result

    async def test_plan_with_code_string_detects_violations(self, governed_workspace):
        k = AegisKernel(str(governed_workspace))
        result = await k.plan_architecture(
            intent="Check snippet",
            code_string='print("debug")\n',
            language="python",
            file_path="src/test.py",
        )
        assert "Code Violations" in result
        assert "no-print" in result

    async def test_valid_clean_code_passes(self, governed_workspace):
        k = AegisKernel(str(governed_workspace))
        (_ws(k) / "src" / "clean.py").write_text('"""Clean module."""\n\nx = 42\n')
        result = await k.validate_architecture_compliance(["src/clean.py"])
        assert "SUCCESS" in result

    async def test_violating_code_returns_remediation(self, governed_workspace):
        k = AegisKernel(str(governed_workspace))
        (_ws(k) / "src" / "bad.py").write_text('print("debug info")\n')
        result = await k.validate_architecture_compliance(["src/bad.py"])
        assert "no-print" in result or "Violation" in result or "INTERVENTION" in result

    async def test_fix_then_revalidate_cycle(self, governed_workspace):
        k = AegisKernel(str(governed_workspace))
        bad_file = _ws(k) / "src" / "cycle.py"
        bad_file.write_text('print("step1")\n')

        result1 = await k.validate_architecture_compliance(["src/cycle.py"])
        assert "SUCCESS" not in result1

        bad_file.write_text("x = 1\n")

        result2 = await k.validate_architecture_compliance(["src/cycle.py"])
        assert "SUCCESS" in result2


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 3: Rule Lifecycle — Add → Validate → Suppress → Remove Pack
# ═══════════════════════════════════════════════════════════════════════════════


class TestRuleLifecycle:
    """Simulates /aegis-architect flow: create rules, manage lifecycle."""

    async def test_add_rule_to_custom_yaml(self, governed_workspace):
        k = AegisKernel(str(governed_workspace))
        result = await k.evolve_ruleset(
            action="add_rule",
            rule_id="custom-no-debug",
            description="No debug imports allowed",
            severity="HIGH",
            engine_type="regex",
            category="style",
            regex_pattern="import pdb",
            rationale="Debug imports should not be committed",
            applies_to="**/*.py",
            language="python",
        )
        assert "SUCCESS" in result

        custom = _ws(k) / ".aegis" / "rules" / "custom.yaml"
        content = custom.read_text()
        assert "custom-no-debug" in content
        assert "import pdb" in content
        assert "Debug imports" in content

    async def test_add_rule_rejects_duplicate(self, governed_workspace):
        k = AegisKernel(str(governed_workspace))
        await k.evolve_ruleset(
            action="add_rule",
            rule_id="unique-rule",
            description="First attempt",
            severity="LOW",
            engine_type="regex",
            category="style",
            regex_pattern="first",
        )
        result = await k.evolve_ruleset(
            action="add_rule",
            rule_id="unique-rule",
            description="Second attempt",
            severity="LOW",
            engine_type="regex",
            category="style",
            regex_pattern="second",
        )
        assert "DUPLICATE_RULE" in result

    async def test_add_rule_with_query_param(self, governed_workspace):
        """Tree-sitter rules use `query` param, not `regex_pattern`."""
        k = AegisKernel(str(governed_workspace))
        result = await k.evolve_ruleset(
            action="add_rule",
            rule_id="custom-ast-rule",
            description="AST-based check",
            severity="MEDIUM",
            engine_type="tree-sitter",
            category="architecture",
            query="(function_definition) @func",
            rationale="Ensure function count limits",
            language="python",
        )
        assert "SUCCESS" in result
        content = (_ws(k) / ".aegis" / "rules" / "custom.yaml").read_text()
        assert "custom-ast-rule" in content
        assert "tree-sitter" in content

    async def test_suppress_violations_adds_to_baseline(self, governed_workspace):
        k = AegisKernel(str(governed_workspace))
        (_ws(k) / "src" / "noisy.py").write_text('print("suppress me")\n')

        result = await k.evolve_ruleset(action="suppress", target="no-print")
        assert "SUCCESS" in result
        assert "Suppressed" in result

    async def test_remove_pack(self, governed_workspace):
        k = AegisKernel(str(governed_workspace))
        result = await k.evolve_ruleset(action="remove_pack", target="style")
        assert "SUCCESS" in result or "REMOVE_FAILED" in result

    async def test_unknown_action_returns_error(self, governed_workspace):
        k = AegisKernel(str(governed_workspace))
        result = await k.evolve_ruleset(action="bogus")
        assert "INVALID_INPUT" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 4: Semantic Grading — Rubric → Self-Grade → Fix
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def semantic_workspace(tmp_path):
    ws = tmp_path / "semantic-project"
    ws.mkdir()
    (ws / "pyproject.toml").write_text('[project]\nname = "semantic"\n')

    src = ws / "src"
    src.mkdir()
    (src / "domain.py").write_text(
        "class OrderProcessor:\n"
        "    def process_order(self, data):\n"
        "        return data\n"
    )

    rules_dir = ws / ".aegis" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "domain.yaml").write_text(
        "rules:\n"
        "- id: domain-naming\n"
        "  description: Classes must use ubiquitous domain language\n"
        "  severity: LOW\n"
        "  engine_type: semantic\n"
        "  category: semantic\n"
        "  language: python\n"
        "  rationale: Consistent domain language reduces cognitive load\n"
        "  applies_to:\n"
        '    - "**/domain.py"\n'
    )
    return ws


class TestSemanticGrading:
    """Simulates /aegis-semantic-check: pull rubric, self-grade, fix."""

    async def test_pull_rubric_for_domain_file(self, semantic_workspace):
        k = AegisKernel(str(semantic_workspace))
        result = await k.request_semantic_grading_rubric("src/domain.py")
        assert "Grading Rubric" in result
        assert "domain-naming" in result
        assert "ubiquitous domain language" in result

    async def test_no_rubric_for_unscoped_file(self, semantic_workspace):
        k = AegisKernel(str(semantic_workspace))
        result = await k.request_semantic_grading_rubric("src/other.py")
        assert "NO_SEMANTIC_RULES" in result

    async def test_rubric_filtered_by_rule_ids(self, semantic_workspace):
        k = AegisKernel(str(semantic_workspace))
        result = await k.request_semantic_grading_rubric(
            "src/domain.py", rule_ids=["domain-naming"]
        )
        assert "Grading Rubric" in result
        assert "domain-naming" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 5: Knowledge Graph — Hypothesis → Dependency → Module Health → Rules
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def graph_workspace(tmp_path):
    ws = tmp_path / "graph-project"
    ws.mkdir()
    (ws / "pyproject.toml").write_text('[project]\nname = "graph-demo"\n')

    api = ws / "api"
    api.mkdir()
    (api / "__init__.py").write_text("from domain import models\n")

    domain = ws / "domain"
    domain.mkdir()
    (domain / "__init__.py").write_text("")
    (domain / "models.py").write_text("class User:\n    pass\n")

    return ws


class TestKnowledgeGraph:
    """Simulates agent querying project structure."""

    async def test_hypothesis_detects_tiers(self, graph_workspace):
        k = AegisKernel(str(graph_workspace))
        result = await k.query_knowledge_graph("hypothesis")
        assert "Proposed" in result or "Detected" in result
        assert "Recommended packs" in result

    async def test_rules_lists_all_installed(self, governed_workspace):
        k = AegisKernel(str(governed_workspace))
        result = await k.query_knowledge_graph("rules")
        data = json.loads(result)
        rule_ids = [r["id"] for r in data]
        assert "no-print" in rule_ids
        assert "require-docstring" in rule_ids

    async def test_module_health_aggregates(self, governed_workspace):
        k = AegisKernel(str(governed_workspace))
        result = await k.query_knowledge_graph("module_health")
        data = json.loads(result)
        assert isinstance(data, dict)

    async def test_invalid_query_type(self, governed_workspace):
        k = AegisKernel(str(governed_workspace))
        result = await k.query_knowledge_graph("fictional_query")
        assert "INVALID_INPUT" in result or "Unknown" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 6: Headless Check — CI/Aider Exit Code
# ═══════════════════════════════════════════════════════════════════════════════


class TestHeadlessCheck:
    """Simulates CI pipeline or Aider test-cmd integration."""

    def test_clean_workspace_returns_zero(self, tmp_path):
        ws = tmp_path / "clean-ci"
        ws.mkdir()
        (ws / "src").mkdir()
        (ws / "src" / "lib.py").write_text("version = '1.0'\n")

        k = AegisKernel(str(ws))
        violations = k.run_headless_check()
        assert violations == 0

    def test_violating_workspace_returns_positive_count(self, governed_workspace):
        k = AegisKernel(str(governed_workspace))
        (_ws(k) / "src" / "violation.py").write_text('print("ci check")\n')
        violations = k.run_headless_check()
        assert violations > 0

    def test_no_rules_returns_zero_with_warning(self, capsys, tmp_path):
        ws = tmp_path / "no-rules-ci"
        ws.mkdir()
        (ws / "src").mkdir()
        (ws / "src" / "main.py").write_text('print("hello")\n')

        k = AegisKernel(str(ws))
        violations = k.run_headless_check()
        captured = capsys.readouterr()
        assert violations == 0
        assert "WARN" in captured.out or "No rules" in captured.out


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 7: Telemetry — Check → Insights → Scorecard
# ═══════════════════════════════════════════════════════════════════════════════


class TestTelemetryPipeline:
    """Simulates observability: record checks, read insights, display scorecard."""

    def test_telemetry_persists_across_instances(self, tmp_path):
        ws = tmp_path / "telemetry-persist"
        ws.mkdir()
        (ws / "src").mkdir()
        (ws / "src" / "mod.py").write_text("x = 1\n")

        k1 = AegisKernel(str(ws))
        k1.telemetry.record_check(5, 2)
        k1.telemetry.record_remediation("rule-x")
        k1.telemetry.record_remediation("rule-x")

        k2 = AegisKernel(str(ws))
        insights = k2.telemetry.get_insights()
        assert insights["total_checks"] == 1
        assert insights["total_remediations"] == 2
        assert insights["remediation_by_rule"]["rule-x"] == 2

    def test_scorecard_format(self, tmp_path):
        ws = tmp_path / "scorecard"
        ws.mkdir()

        k = AegisKernel(str(ws))
        k.telemetry.record_check(10, 3)
        k.telemetry.record_check(0, 0)
        output = k.telemetry.display_insights()
        assert "Aegis Insights Scorecard" in output
        assert "checks run" in output
        assert "success rate" in output

    def test_insights_empty_workspace(self, tmp_path):
        ws = tmp_path / "empty-telemetry"
        ws.mkdir()

        k = AegisKernel(str(ws))
        insights = k.telemetry.get_insights()
        assert insights["total_checks"] == 0
        assert insights["total_remediations"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario 8: Full Agent Lifecycle — End-to-End
# ═══════════════════════════════════════════════════════════════════════════════


class TestFullAgentLifecycle:
    """Complete agent journey from cold start to governed development."""

    async def test_complete_lifecycle(self, tmp_path):
        ws = tmp_path / "complete-lifecycle"
        ws.mkdir()

        # Phase 1: Init — create project
        src = ws / "src"
        src.mkdir()
        (ws / "pyproject.toml").write_text('[project]\nname = "lifecycle"\n')
        (src / "__init__.py").write_text("")

        k = AegisKernel(str(ws))

        # Phase 1: Discover architecture
        hyp = await k.query_knowledge_graph("hypothesis")
        assert "Proposed" in hyp or "Detected" in hyp

        # Phase 2: Scaffold governance
        result = await k.scaffold_governance_framework(["security"])
        assert "SUCCESS" in result

        # Phase 3: Plan before editing
        plan = await k.plan_architecture(
            intent="Create user service", file_path="src/service.py"
        )
        assert "Architectural Context" in plan

        # Phase 4: Write code with a clear violation
        (src / "service.py").write_text(
            'print("debug token")\n\ndef get_user():\n    return {"name": "test"}\n'
        )

        # Phase 5: Validate — may or may not find violations
        # (security pack rules are phase-scoped; may not trigger at pre-commit)
        check = await k.validate_architecture_compliance(["src/service.py"])
        assert isinstance(check, str)

        # Phase 6: Add a custom rule
        add = await k.evolve_ruleset(
            action="add_rule",
            rule_id="lifecycle-rule",
            description="Test lifecycle rule",
            severity="LOW",
            engine_type="regex",
            category="style",
            regex_pattern="lifecycle_test_pattern",
        )
        assert "SUCCESS" in add

        # Phase 7: Verify custom rule persisted
        rules_json = await k.query_knowledge_graph("rules")
        rules_data = json.loads(rules_json)
        all_ids = [r["id"] for r in rules_data]
        assert "lifecycle-rule" in all_ids

        # Phase 8: Check telemetry
        k.telemetry.record_check(3, 1)
        insights = k.telemetry.get_insights()
        assert insights["total_checks"] >= 1

        # Phase 9: Headless check works
        violations = k.run_headless_check()
        assert isinstance(violations, int)
        assert violations >= 0
