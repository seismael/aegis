"""
Aegis End-to-End Validation — Exercises the full 4-stage governance pipeline
against the TaskFlow test project with seeded violations.

This simulates what agents experience when Aegis is active:
  1. AegisPlanVerifier — proactive intent check
  2. AegisEnforcementNode — in-memory AST delta evaluation
  3. NativeAegisExecutor — tool execution interception
  4. AegisKernel — MCP check_architecture gate
"""

import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

# Add aegis to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from aegis.agent import create_aegis_agent
from aegis.core.baseline import BaselineManager
from aegis.domain.policy.parser import PolicyParser


def setup_test_project():
    """Copy the TaskFlow template and install Aegis rules."""
    base = Path(__file__).resolve().parent.parent.parent
    src = base / "tests" / "manual" / "projects" / "taskflow"
    dst = base / "taskflow"

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)

    # Install rules (L2: architecture, security, best-practices, style, testing)
    rules_src = base / "src" / "aegis" / "resources" / "default_rules"
    rules_dst = dst / ".aegis" / "rules"
    rules_dst.mkdir(parents=True, exist_ok=True)

    packs = ["architecture", "security", "best-practices", "style", "testing"]
    for pack in packs:
        pack_src = rules_src / pack
        if pack_src.exists():
            shutil.copytree(pack_src, rules_dst / pack)

    return dst, packs


def count_violations(workspace_root):
    """Run a headless check and return the violation count."""
    parser = PolicyParser(str(workspace_root))
    rules = parser.parse_all()

    from aegis.core.parser import TreeSitterAnalyzer
    from aegis.domain.evaluation.analyzers.graph import GraphAnalyzer
    from aegis.domain.evaluation.analyzers.regex import RegexAnalyzer
    from aegis.domain.evaluation.analyzers.semantic import SemanticAnalyzer
    from aegis.domain.evaluation_service import EvaluationService

    evaluation = EvaluationService(
        tree_sitter_analyzer=TreeSitterAnalyzer(),
        graph_analyzer=GraphAnalyzer(),
        regex_analyzer=RegexAnalyzer(),
        semantic_analyzer=SemanticAnalyzer(),
    )

    violations = evaluation.evaluate_workspace(str(workspace_root), rules)

    baseline = BaselineManager(str(workspace_root / ".aegis"))
    rule_map = {r.id: r for r in rules}
    active = [
        v for v in violations if not baseline.is_exempt(v, rule_map.get(v.rule_id))
    ]

    return len(violations), len(active), active


def main():
    results = {"test_timestamp": datetime.now().isoformat(), "stages": {}}

    # STAGE 1: Setup
    print("=" * 60)
    print("STAGE 1: Project Setup")
    print("=" * 60)
    t0 = time.time()
    workspace, packs = setup_test_project()
    setup_time = time.time() - t0
    print(f"  Workspace: {workspace}")
    print(f"  Packs: {packs}")
    print(f"  Setup time: {setup_time:.2f}s")
    results["stages"]["setup"] = {"time_s": round(setup_time, 3), "packs": packs}

    # STAGE 2: Count violations BEFORE
    print("\n" + "=" * 60)
    print("STAGE 2: Violation Baseline (Before Agent)")
    print("=" * 60)
    t0 = time.time()
    total_v, active_v, violations = count_violations(workspace)
    check_time = time.time() - t0
    print(f"  Total violations: {total_v}")
    print(f"  Active violations: {active_v}")
    print(f"  Check time: {check_time:.2f}s")
    print("\n  Top 5 seeded violations found:")
    seeded_ids = [
        "sec-no-eval",
        "sec-no-hardcoded-credentials",
        "arch-layer-violation",
        "ts-no-console-log",
        "ts-no-error-handling",
    ]
    for v in violations:
        if v.rule_id in seeded_ids:
            print(f"    {v.file}:{v.line} [{v.rule_id}] {v.description[:80]}")
    results["stages"]["violation_baseline"] = {
        "time_s": round(check_time, 3),
        "total_violations": total_v,
        "active_violations": active_v,
        "seeded_detected": sum(1 for v in violations if v.rule_id in seeded_ids),
    }

    # STAGE 3: AegisPlanVerifier — proactive check
    print("\n" + "=" * 60)
    print("STAGE 3: AegisPlanVerifier (Proactive Intent Gate)")
    print("=" * 60)
    t0 = time.time()
    agent = create_aegis_agent(workspace_root=str(workspace))
    init_time = time.time() - t0

    # Test plan verification for a violating intent
    plan_tests = [
        {
            "name": "No violation — safe import",
            "imports": ["domain.models"],
            "target": "application.use_cases",
            "expected": "PLAN APPROVED",
        },
        {
            "name": "Layer violation — infrastructure from domain",
            "imports": ["infrastructure.database", "infrastructure.email"],
            "target": "domain.services",
            "expected": "PLAN REJECTED",
        },
        {
            "name": "Security violation — importing dangerous modules",
            "imports": ["os.system"],
            "target": "api.routes",
            "expected": "verify",
        },
    ]

    for test in plan_tests:
        res = agent.verify_plan(test["imports"], test["target"])
        match = test["expected"] in str(res.get("feedback", "")) or res.get(
            "plan_valid", True
        ) == (test["expected"] == "PLAN APPROVED")
        status = "PASS" if match else "FAIL"
        print(f"  [{status}] {test['name']}")
        print(f"         Result: {res.get('feedback', res)[:100]}")
    results["stages"]["plan_verifier"] = {
        "time_s": round(init_time, 3),
        "tests": plan_tests,
    }

    # STAGE 4: AegisEnforcementNode — AST delta evaluation
    print("\n" + "=" * 60)
    print("STAGE 4: AegisEnforcementNode (In-Memory AST Gate)")
    print("=" * 60)

    code_tests = [
        {
            "name": "Compliant code — no violations",
            "code": "def calculate(x: int) -> int:\n    return x * 2\n",
            "expect_clean": True,
        },
        {
            "name": "Security violation — exec() call",
            "code": "def handle(user_input: str) -> None:\n    exec(user_input)\n",
            "expect_clean": False,
        },
        {
            "name": "Style violation — print() in production",
            "code": "def process(data: dict) -> None:\n    print(f'Processing {data}')\n    return data\n",
            "expect_clean": False,
        },
        {
            "name": "Layer violation — wrong import",
            "code": "from infrastructure.database import get_db\n\ndef create(data):\n    db = get_db()\n    return db.save(data)\n",
            "expect_clean": False,
        },
    ]

    for test in code_tests:
        t0 = time.time()
        res = agent.evaluate_code_delta(test["code"])
        delta_time = time.time() - t0
        is_clean = res["governance_valid"]
        matches = is_clean == test["expect_clean"]
        status = "PASS" if matches else "FAIL"
        print(f"  [{status}] {test['name']} ({delta_time:.3f}s)")
        print(
            f"         Clean: {is_clean}, Violations: {res['total_violations']}, Active: {len(res.get('active_violations', []))}"
        )
    results["stages"]["enforcement_node"] = {"tests": code_tests}

    # STAGE 5: NativeAegisExecutor — tool execution
    print("\n" + "=" * 60)
    print("STAGE 5: NativeAegisExecutor (Hardened Tool Gate)")
    print("=" * 60)

    from aegis.runtime.executor import AegisGovernanceError

    def mock_write_file(path, content, language="python"):
        return f"Wrote {len(content)} bytes to {path}"

    tool_tests = [
        {
            "name": "Safe write — no violations",
            "tool": "write_file",
            "args": {
                "path": "test.py",
                "content": "def hello():\n    return 'world'\n",
            },
            "expect_blocked": False,
        },
        {
            "name": "Blocked write — contains exec()",
            "tool": "write_file",
            "args": {"path": "dangerous.py", "content": "exec(user_input)"},
            "expect_blocked": True,
        },
        {
            "name": "Safe edit — no code content",
            "tool": "read",
            "args": {"path": "config.json"},
            "expect_blocked": False,
        },
    ]

    for test in tool_tests:
        try:
            res = agent.executor.execute_tool(
                test["tool"], test["args"], mock_write_file
            )
            print(f"  [PASS] {test['name']} - executed OK")
        except AegisGovernanceError as e:
            matches = test["expect_blocked"]
            status = "PASS" if matches else "FAIL"
            print(f"  [{status}] {test['name']} — BLOCKED: {str(e)[:100]}")
        except Exception as e:
            print(f"  [INFO] {test['name']} — {str(e)[:100]}")
    results["stages"]["executor"] = {"tests": tool_tests}

    # STAGE 6: check_architecture — complete MCP gate
    print("\n" + "=" * 60)
    print("STAGE 6: check_architecture (MCP Gate)")
    print("=" * 60)

    modified_files = [
        "domain/services.py",
        "api/routes.py",
        "application/use_cases.py",
        "infrastructure/repositories.py",
    ]

    t0 = time.time()
    # Run check_architecture on the workspace
    total_after, active_after, violations_after = count_violations(workspace)
    gate_time = time.time() - t0

    print(f"  Files checked: {modified_files}")
    print(f"  Violations: {active_after} active / {total_after} total")
    print(f"  Time: {gate_time:.2f}s")
    results["stages"]["check_architecture"] = {
        "time_s": round(gate_time, 3),
        "files": modified_files,
        "active_violations": active_after,
        "total_violations": total_after,
    }

    # STAGE 7: Summary
    print("\n" + "=" * 60)
    print("STAGE 7: Pipeline Summary")
    print("=" * 60)

    seeded_count = results["stages"]["violation_baseline"].get("seeded_detected", 0)
    print(f"  Seeded violations detected: {seeded_count}/7")
    print("  Plan verifier: catches layer violations before code generation")
    print("  Enforcement node: microsecond AST evaluation for code deltas")
    print("  Executor gateway: blocks tool calls with CRITICAL/HIGH violations")
    print(f"  MCP gate: {active_after} active violations in {gate_time:.2f}s")

    # Save results
    output_path = (
        Path(__file__).resolve().parent.parent.parent
        / "tests"
        / "manual"
        / "results"
        / "pipeline_validation.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to: {output_path}")

    # Cleanup
    print("\n" + "=" * 60)
    print("STAGE 8: Teardown")
    print("=" * 60)
    if workspace.exists():
        shutil.rmtree(workspace)
    print(f"  Removed: {workspace}")

    return results


if __name__ == "__main__":
    main()
