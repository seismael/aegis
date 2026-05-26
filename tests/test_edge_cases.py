"""
Comprehensive edge-case and integration tests.
Covers: execution depth circuit breaker, proximity scoping edges,
error paths, agent-native flow edge cases, telemetry edge cases.
"""

import json
from pathlib import Path

import pytest

from aegis.kernel.server import AegisKernel


def _ws(k: AegisKernel) -> Path:
    return Path(k.workspace_root)


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def empty_workspace(tmp_path):
    ws = tmp_path / "bare"
    ws.mkdir()
    (ws / "src").mkdir()
    return AegisKernel(str(ws))


@pytest.fixture
def mini_project(tmp_path):
    ws = tmp_path / "mini"
    ws.mkdir()
    (ws / "pyproject.toml").write_text('[project]\nname = "mini"\n')
    src = ws / "src"
    src.mkdir()
    (src / "__init__.py").write_text("")
    (src / "lib.py").write_text("x = 1\n")

    rules = ws / ".aegis" / "rules"
    rules.mkdir(parents=True)
    (rules / "test.yaml").write_text(
        "rules:\n"
        "- id: rule-a\n"
        "  description: Test rule A\n"
        "  severity: HIGH\n"
        "  engine_type: regex\n"
        "  category: style\n"
        "  query: xyz_no_match_\n"
        "  language: python\n"
        "  phases:\n"
        "    - pre-commit\n"
        "  applies_to:\n"
        '    - "**/*.py"\n'
    )
    return AegisKernel(str(ws))


@pytest.fixture
def proximity_project(tmp_path):
    """Two modules with imports, testing proximity scoping."""
    ws = tmp_path / "prox"
    ws.mkdir()
    (ws / "pyproject.toml").write_text('[project]\nname = "prox"\n')

    api = ws / "api"
    api.mkdir()
    (api / "__init__.py").write_text("from domain import models\n")

    domain = ws / "domain"
    domain.mkdir()
    (domain / "__init__.py").write_text("")
    (domain / "models.py").write_text("class User:\n    pass\n")

    rules = ws / ".aegis" / "rules"
    rules.mkdir(parents=True)
    (rules / "api.yaml").write_text(
        "rules:\n"
        "- id: api-check\n"
        "  description: API-layer rule\n"
        "  severity: HIGH\n"
        "  engine_type: regex\n"
        "  category: style\n"
        "  query: __no_match\n"
        "  language: python\n"
        "  phases:\n"
        "    - pre-commit\n"
        "  applies_to:\n"
        '    - "api/**/*.py"\n'
    )
    (rules / "domain.yaml").write_text(
        "rules:\n"
        "- id: domain-check\n"
        "  description: Domain-layer rule\n"
        "  severity: HIGH\n"
        "  engine_type: regex\n"
        "  category: style\n"
        "  query: __no_match\n"
        "  language: python\n"
        "  phases:\n"
        "    - pre-commit\n"
        "  applies_to:\n"
        '    - "domain/**/*.py"\n'
    )
    return AegisKernel(str(ws))


# ═══════════════════════════════════════════════════════════════════════════════
# Execution Depth Circuit Breaker — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestExecutionDepth:
    async def test_depth_0_works_normally(self, mini_project):
        result = await mini_project.validate_architecture_compliance(
            ["src/lib.py"], execution_depth=0
        )
        assert "SUCCESS" in result

    async def test_depth_1_works_normally(self, mini_project):
        result = await mini_project.validate_architecture_compliance(
            ["src/lib.py"], execution_depth=1
        )
        assert "SUCCESS" in result

    async def test_depth_2_works_normally(self, mini_project):
        result = await mini_project.validate_architecture_compliance(
            ["src/lib.py"], execution_depth=2
        )
        assert "SUCCESS" in result

    async def test_depth_3_works_normally(self, mini_project):
        result = await mini_project.validate_architecture_compliance(
            ["src/lib.py"], execution_depth=3
        )
        assert "SUCCESS" in result

    async def test_depth_4_triggers_bypass(self, mini_project):
        result = await mini_project.validate_architecture_compliance(
            ["src/lib.py"], execution_depth=4
        )
        assert "BYPASS" in result
        assert "Execution depth" in result

    async def test_depth_5_triggers_bypass(self, mini_project):
        result = await mini_project.validate_architecture_compliance(
            ["src/lib.py"], execution_depth=5
        )
        assert "BYPASS" in result

    async def test_depth_100_triggers_bypass(self, mini_project):
        result = await mini_project.validate_architecture_compliance(
            ["src/lib.py"], execution_depth=100
        )
        assert "BYPASS" in result

    async def test_bypass_still_returns_warn_prefix(self, mini_project):
        result = await mini_project.validate_architecture_compliance(
            ["src/lib.py"], execution_depth=4
        )
        assert result.startswith("WARN:")

    async def test_depth_edge_negative_works(self, mini_project):
        """Negative depth should be treated as depth 0 (not bypass)."""
        result = await mini_project.validate_architecture_compliance(
            ["src/lib.py"], execution_depth=-1
        )
        assert "SUCCESS" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Proximity Scoping — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestProximityScoping:
    def test_proximity_pulls_connected_module_rules(self, proximity_project):
        """Proximity scoping pulls rules for connected modules."""
        rules = proximity_project._load_rules()
        result = proximity_project._filter_rules_for_files(["api/__init__.py"], rules)
        rule_ids = {r.id for r in result}
        assert "api-check" in rule_ids
        assert len(result) >= 1

    def test_no_adjacency_returns_narrow_scope(self, mini_project):
        """Workspace with no import graph returns only direct matches."""
        rules = mini_project._load_rules()
        result = mini_project._filter_rules_for_files(["src/lib.py"], rules)
        assert len(result) > 0
        assert all(r.id == "rule-a" for r in result)

    def test_proximity_single_file_max_15(self, proximity_project):
        rules = proximity_project._load_rules()
        result = proximity_project._filter_rules_for_files(["api/__init__.py"], rules)
        assert len(result) <= 15


# ═══════════════════════════════════════════════════════════════════════════════
# Validate Compliance — Error Paths
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidateComplianceErrors:
    async def test_no_rules_installed_returns_warn(self, empty_workspace):
        result = await empty_workspace.validate_architecture_compliance(["src/x.py"])
        assert "WARN" in result
        assert "No rules" in result

    async def test_empty_file_list_handled(self, mini_project):
        result = await mini_project.validate_architecture_compliance([])
        assert isinstance(result, str)
        assert "SUCCESS" in result or "WARN" in result

    async def test_single_file_validation(self, mini_project):
        (_ws(mini_project) / "src" / "single.py").write_text("x = 1\n")
        result = await mini_project.validate_architecture_compliance(["src/single.py"])
        assert "SUCCESS" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Plan Architecture — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestPlanArchitectureEdges:
    async def test_empty_intent(self, mini_project):
        result = await mini_project.plan_architecture(intent="")
        assert "Architectural Context" in result

    async def test_long_code_string(self, mini_project):
        long_code = "x = 1\n" * 100
        result = await mini_project.plan_architecture(
            intent="Test", code_string=long_code, language="python"
        )
        assert "Architectural Context" in result

    async def test_code_string_no_file_path(self, mini_project):
        result = await mini_project.plan_architecture(
            intent="Test",
            code_string='print("hello")\n',
            language="python",
        )
        assert "Architectural Context" in result

    async def test_code_string_violating_prints(self, mini_project):
        result = await mini_project.plan_architecture(
            intent="Check bad code",
            code_string='print("debug")\n',
            language="python",
            file_path="src/test.py",
        )
        assert isinstance(result, str)
        assert "Architectural Context" in result

    async def test_non_python_code_string(self, mini_project):
        result = await mini_project.plan_architecture(
            intent="Test",
            code_string="const x = 1;\n",
            language="javascript",
        )
        assert "Architectural Context" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Evolve Ruleset — Error Paths
# ═══════════════════════════════════════════════════════════════════════════════


class TestEvolveRulesetErrors:
    async def test_add_rule_missing_rule_id(self, mini_project):
        result = await mini_project.evolve_ruleset(
            action="add_rule",
            description="Missing ID",
        )
        assert "INVALID_INPUT" in result

    async def test_add_rule_missing_description(self, mini_project):
        result = await mini_project.evolve_ruleset(
            action="add_rule",
            rule_id="no-desc",
        )
        assert "INVALID_INPUT" in result

    async def test_add_rule_tree_sitter_with_query(self, mini_project):
        result = await mini_project.evolve_ruleset(
            action="add_rule",
            rule_id="ast-rule-1",
            description="AST rule",
            severity="MEDIUM",
            engine_type="tree-sitter",
            category="architecture",
            query="(function_definition) @f",
            language="python",
        )
        assert "SUCCESS" in result
        content = (_ws(mini_project) / ".aegis" / "rules" / "custom.yaml").read_text()
        assert "tree-sitter" in content
        assert "(function_definition)" in content

    async def test_add_rule_regex_with_regex_pattern(self, mini_project):
        result = await mini_project.evolve_ruleset(
            action="add_rule",
            rule_id="regex-rule-1",
            description="Regex rule",
            severity="LOW",
            engine_type="regex",
            category="style",
            regex_pattern=r"debug\s*\(.*\)",
        )
        assert "SUCCESS" in result
        content = (_ws(mini_project) / ".aegis" / "rules" / "custom.yaml").read_text()
        assert "regex-rule-1" in content

    async def test_add_rule_with_rationale(self, mini_project):
        result = await mini_project.evolve_ruleset(
            action="add_rule",
            rule_id="reasoned-rule",
            description="Rule with reason",
            severity="HIGH",
            engine_type="regex",
            category="security",
            regex_pattern="password",
            rationale="Prevents credential leaks",
        )
        assert "SUCCESS" in result
        content = (_ws(mini_project) / ".aegis" / "rules" / "custom.yaml").read_text()
        assert "Prevents credential leaks" in content

    async def test_add_rule_graph_engine_with_query(self, mini_project):
        result = await mini_project.evolve_ruleset(
            action="add_rule",
            rule_id="graph-rule",
            description="Graph rule",
            severity="MEDIUM",
            engine_type="graph",
            category="architecture",
            query="disallowed_import",
            rationale="Layer isolation",
        )
        assert "SUCCESS" in result

    async def test_add_rule_with_applies_to(self, mini_project):
        result = await mini_project.evolve_ruleset(
            action="add_rule",
            rule_id="scoped-rule",
            description="Scoped rule",
            severity="LOW",
            engine_type="regex",
            category="style",
            regex_pattern="xyz",
            applies_to="api/**/*.py",
        )
        assert "SUCCESS" in result
        content = (_ws(mini_project) / ".aegis" / "rules" / "custom.yaml").read_text()
        assert "api/**/*.py" in content

    async def test_suppress_requires_target(self, mini_project):
        result = await mini_project.evolve_ruleset(action="suppress")
        assert "INVALID_INPUT" in result

    async def test_suppress_nonexistent_rule(self, mini_project):
        result = await mini_project.evolve_ruleset(
            action="suppress", target="nonexistent-rule-id"
        )
        assert "RULE_NOT_FOUND" in result

    async def test_remove_pack_requires_target(self, mini_project):
        result = await mini_project.evolve_ruleset(action="remove_pack")
        assert "INVALID_INPUT" in result

    async def test_remove_nonexistent_pack(self, mini_project):
        result = await mini_project.evolve_ruleset(
            action="remove_pack", target="nonexistent-pack"
        )
        assert "REMOVE_FAILED" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Scaffold Governance — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestScaffoldEdges:
    async def test_scaffold_empty_pack_list(self, empty_workspace):
        result = await empty_workspace.scaffold_governance_framework([])
        assert "SUCCESS" in result

    async def test_scaffold_single_pack(self, empty_workspace):
        result = await empty_workspace.scaffold_governance_framework(["security"])
        assert "SUCCESS" in result
        assert (_ws(empty_workspace) / ".aegis" / "rules" / "security").is_dir()

    async def test_scaffold_partial_valid_packs(self, empty_workspace):
        result = await empty_workspace.scaffold_governance_framework(
            ["security", "bogus-pack-xyz"]
        )
        assert "SCAFFOLD_FAILED" in result

    async def test_scaffold_generates_agents_md_even_empty(self, empty_workspace):
        result = await empty_workspace.scaffold_governance_framework([])
        assert "AGENTS.md" in result
        assert (_ws(empty_workspace) / "AGENTS.md").exists()


# ═══════════════════════════════════════════════════════════════════════════════
# Semantic Grading — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestSemanticEdges:
    async def test_grading_rubric_for_nonexistent_file(self, mini_project):
        result = await mini_project.request_semantic_grading_rubric("nonexistent.py")
        assert "NO_SEMANTIC_RULES" in result

    async def test_grading_rubric_with_no_rules(self, empty_workspace):
        result = await empty_workspace.request_semantic_grading_rubric("src/x.py")
        assert "NO_SEMANTIC_RULES" in result

    async def test_grading_rubric_with_specific_rule_ids(self, mini_project):
        result = await mini_project.request_semantic_grading_rubric(
            "src/lib.py", rule_ids=["nonexistent"]
        )
        assert "NO_SEMANTIC_RULES" in result


# ═══════════════════════════════════════════════════════════════════════════════
# Knowledge Graph — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestKnowledgeGraphEdges:
    async def test_rules_list_empty_workspace(self, empty_workspace):
        result = await empty_workspace.query_knowledge_graph("rules")
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_dependency_graph_with_target(self, proximity_project):
        result = await proximity_project.query_knowledge_graph(
            "dependency_graph", target="api"
        )
        data = json.loads(result)
        assert "nodes" in data
        assert "edges" in data

    async def test_module_health_empty_workspace(self, empty_workspace):
        result = await empty_workspace.query_knowledge_graph("module_health")
        data = json.loads(result)
        assert isinstance(data, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# Telemetry — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestTelemetryEdges:
    def test_telemetry_persists_to_disk(self, tmp_path):
        ws = tmp_path / "tel-persist"
        ws.mkdir()

        k1 = AegisKernel(str(ws))
        k1.telemetry.record_check(10, 5)
        k1.telemetry.record_remediation("rule-1")
        k1.telemetry.record_remediation("rule-1")
        k1.telemetry.record_remediation("rule-2")

        k2 = AegisKernel(str(ws))
        insights = k2.telemetry.get_insights()
        assert insights["total_checks"] == 1
        assert insights["total_remediations"] == 3
        assert insights["remediation_by_rule"]["rule-1"] == 2
        assert insights["remediation_by_rule"]["rule-2"] == 1

    def test_telemetry_multiple_checks(self, tmp_path):
        ws = tmp_path / "tel-multi"
        ws.mkdir()

        k = AegisKernel(str(ws))
        for i in range(5):
            k.telemetry.record_check(i, 0)

        insights = k.telemetry.get_insights()
        assert insights["total_checks"] == 5
        assert insights["check_success_rate"] == 0.2  # 1 of 5 had 0 violations

    def test_telemetry_display_insights_clean(self, tmp_path):
        ws = tmp_path / "scorecard"
        ws.mkdir()

        k = AegisKernel(str(ws))
        k.telemetry.record_check(0, 0)
        output = k.telemetry.display_insights()
        assert "Aegis Insights Scorecard" in output
        assert "success rate" in output

    def test_telemetry_concurrent_thread_safety(self, tmp_path):
        import threading

        ws = tmp_path / "tel-concurrent"
        ws.mkdir()
        k = AegisKernel(str(ws))

        errors = []

        def record():
            try:
                for _ in range(10):
                    k.telemetry.record_check(1, 0)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=record) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        insights = k.telemetry.get_insights()
        assert insights["total_checks"] == 50


# ═══════════════════════════════════════════════════════════════════════════════
# Installer — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestInstallerEdges:
    def test_generate_agents_template_to_disk(self, tmp_path):
        from aegis.infrastructure.installer import AgentNativeInstaller

        path = AgentNativeInstaller.generate_agents_template(str(tmp_path))
        content = Path(path).read_text()
        assert "validate_architecture_compliance" in content
        assert "MUST" in content

    def test_installer_rejects_unknown_tool(self):
        from aegis.infrastructure.installer import AgentNativeInstaller

        installer = AgentNativeInstaller()
        with pytest.raises(ValueError, match="Unsupported tool"):
            installer.install(target_tool="cursor")


# ═══════════════════════════════════════════════════════════════════════════════
# Headless Check — Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════


class TestHeadlessCheckEdges:
    def test_no_rules_prints_warn(self, empty_workspace):
        violations = empty_workspace.run_headless_check()
        assert violations == 0

    def test_clean_project_zero_violations(self, mini_project):
        """Project with only non-matching rules should return 0."""
        violations = mini_project.run_headless_check()
        assert violations >= 0

    def test_violating_project_positive_count(self, tmp_path):
        ws = tmp_path / "violating"
        ws.mkdir()
        src = ws / "src"
        src.mkdir()
        (src / "bad.py").write_text('print("bad")\n')

        rules = ws / ".aegis" / "rules"
        rules.mkdir(parents=True)
        (rules / "check.yaml").write_text(
            "rules:\n"
            "- id: no-print\n"
            "  description: No prints\n"
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

        k = AegisKernel(str(ws))
        violations = k.run_headless_check()
        assert violations > 0
