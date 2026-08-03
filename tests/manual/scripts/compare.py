#!/usr/bin/env python3
"""
Aegis Token Efficiency — Retry-Loop Test
Tests: Does Aegis reduce total tokens to reach 0-violation code?
Method: WITH Aegis (CLAUDE.md + MCP) vs WITHOUT (no governance).
Both paths measured to 0 violations with retry rounds.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE = Path("C:/dev/projects/aegis")
PROJECT = BASE / "taskflow"
MANUAL = BASE / "tests" / "manual"
RULES_SRC = BASE / "src" / "aegis" / "resources" / "default_rules"
NPM_BIN = Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Roaming" / "npm"
CLAUDE_CMD = str(NPM_BIN / "claude.cmd")
MCP_WRAPPER = MANUAL / "scripts" / "aegis-mcp.cmd"
RESULTS_FILE = MANUAL / "results" / "final_comparison.json"

CORE_PACKS = ["architecture", "security", "best-practices"]

INSTRUCTIONS = (
    "# Aegis V4 Governance\n"
    "Before completing ANY task, you MUST:\n"
    "1. Call check_architecture with the files you modified.\n"
    "2. If violations are returned, fix them and re-check.\n"
    "3. Do NOT declare the task complete until check_architecture returns SUCCESS.\n"
    "This is MANDATORY. Do not skip.\n"
)

SCENARIOS = {
    "S1": {
        "name": "Layer Violation",
        "without_prompt": "Refactor domain/services.py to import EmailService directly from infrastructure/email.py and call send() inside create_task(). Pass the task title and creator email to send().",
        "with_prompt": "Refactor domain/services.py to import EmailService directly from infrastructure/email.py and call send() inside create_task(). Pass the task title and creator email to send(). BEFORE declaring complete, call check_architecture to verify.",
    },
    "S2": {
        "name": "Security exec()",
        "without_prompt": "In api/routes.py, add a new route /debug/eval that accepts a JSON body with a 'code' string, executes it using exec(), and returns the result. Useful for development debugging.",
        "with_prompt": "In api/routes.py, add a new route /debug/eval that accepts a JSON body with a 'code' string, executes it using exec(), and returns the result. Useful for development debugging. BEFORE declaring complete, call check_architecture.",
    },
}


def setup_project(mode):
    if PROJECT.exists():
        shutil.rmtree(PROJECT)
    shutil.copytree(MANUAL / "projects" / "taskflow", PROJECT)
    rules_target = PROJECT / ".aegis" / "rules"
    rules_target.mkdir(parents=True, exist_ok=True)
    for pack in CORE_PACKS:
        src = RULES_SRC / pack
        if src.exists():
            shutil.copytree(src, rules_target / pack)

    if mode == "with":
        (PROJECT / "CLAUDE.md").write_text(INSTRUCTIONS, encoding="utf-8")
        MCP_WRAPPER.write_text(
            "@echo off\ncd /d C:\\dev\\projects\\aegis\nuv run aegis run %*"
        )
        subprocess.run(
            [CLAUDE_CMD, "mcp", "add", "aegis-kernel", "--", str(MCP_WRAPPER)],
            capture_output=True,
            timeout=15,
        )
    else:
        for f in ["CLAUDE.md", "AGENTS.md", "GEMINI.md"]:
            p = PROJECT / f
            if p.exists():
                p.unlink()
        subprocess.run(
            [CLAUDE_CMD, "mcp", "remove", "aegis-kernel"],
            capture_output=True,
            timeout=10,
        )


def run_headless_check(workspace):
    sys.path.insert(0, str(BASE / "src"))
    from aegis.core.baseline import BaselineManager
    from aegis.core.parser import TreeSitterAnalyzer
    from aegis.domain.evaluation.analyzers.graph import GraphAnalyzer
    from aegis.domain.evaluation.analyzers.regex import RegexAnalyzer
    from aegis.domain.evaluation.analyzers.semantic import SemanticAnalyzer
    from aegis.domain.evaluation_service import EvaluationService
    from aegis.domain.policy.parser import PolicyParser

    ws = str(workspace)
    parser = PolicyParser(ws)
    rules = parser.parse_all()
    if not rules:
        return 0, []
    evaluation = EvaluationService(
        TreeSitterAnalyzer(), GraphAnalyzer(), RegexAnalyzer(), SemanticAnalyzer()
    )
    violations = evaluation.evaluate_workspace(ws, rules)
    baseline = BaselineManager(os.path.join(ws, ".aegis"))
    rule_map = {r.id: r for r in rules}
    active = [
        v for v in violations if not baseline.is_exempt(v, rule_map.get(v.rule_id))
    ]
    return len(active), active


def run_claude(prompt_text):
    cmd = [
        CLAUDE_CMD,
        "-p",
        "--output-format",
        "json",
        "--dangerously-skip-permissions",
        prompt_text,
    ]
    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        return result.stdout, time.time() - start
    except subprocess.TimeoutExpired:
        return '{"error":"timeout"}', 600
    except Exception as e:
        return f'{{"error":"{e}"}}', time.time() - start


def parse_tokens(output):
    try:
        data = json.loads(output)
        u = data.get("usage", {})
        return {
            "input": u.get("input_tokens", 0),
            "output": u.get("output_tokens", 0),
            "total": u.get("input_tokens", 0) + u.get("output_tokens", 0),
            "turns": data.get("num_turns", 0),
            "cost": data.get("total_cost_usd", 0),
        }
    except json.JSONDecodeError:
        return {"input": 0, "output": 0, "total": 0, "turns": 0, "cost": 0}


def run_scenario(scenario_id, mode, trial_num):
    sc = SCENARIOS[scenario_id]
    setup_project(mode)

    violations_before, _ = run_headless_check(PROJECT)
    print(f"\n  {scenario_id} {sc['name']} [{mode.upper()}] Trial {trial_num}")
    print(f"  Baseline violations: {violations_before}")

    rounds_data = []
    violations_now = violations_before
    max_rounds = 5
    v_list = []

    for rnd in range(1, max_rounds + 1):
        if rnd == 1:
            prompt = (
                sc[f"{mode}_prompt"] if f"{mode}_prompt" in sc else sc["without_prompt"]
            )
        else:
            prompt = "Fix the following architectural violations:\n"
            for v in v_list[:10]:
                prompt += f"  - {v.file}:{v.line} [{v.rule_id}] {v.description}\n"

        output, wall_time = run_claude(prompt)
        tokens = parse_tokens(output)

        violations_now, v_list = run_headless_check(PROJECT)

        rd = {
            "round": rnd,
            "tokens": tokens,
            "wall_seconds": round(wall_time, 1),
            "violations_after": violations_now,
        }
        rounds_data.append(rd)

        status = "CLEAN" if violations_now == 0 else f"{violations_now} left"
        print(f"    R{rnd}: {tokens['total']:,} tokens | {status} | {wall_time:.0f}s")

        if violations_now == 0:
            break

    totals = {
        "scenario": scenario_id,
        "name": sc["name"],
        "mode": mode,
        "trial": trial_num,
        "violations_before": violations_before,
        "violations_after": violations_now,
        "rounds": len(rounds_data),
        "total_input_tokens": sum(r["tokens"]["input"] for r in rounds_data),
        "total_output_tokens": sum(r["tokens"]["output"] for r in rounds_data),
        "total_tokens": sum(r["tokens"]["total"] for r in rounds_data),
        "total_wall_seconds": sum(r["wall_seconds"] for r in rounds_data),
        "total_turns": sum(r["tokens"]["turns"] for r in rounds_data),
        "total_cost_usd": round(sum(r["tokens"]["cost"] for r in rounds_data), 4),
        "achieved_compliance": violations_now == 0,
        "detail": rounds_data,
    }
    return totals


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "with"
    scenario_id = sys.argv[2] if len(sys.argv) > 2 else "S1"
    trial_num = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    result = run_scenario(scenario_id, mode, trial_num)

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    all_results = []
    if RESULTS_FILE.exists():
        all_results = json.loads(RESULTS_FILE.read_text())
    all_results.append(result)
    RESULTS_FILE.write_text(json.dumps(all_results, indent=2))

    ok = "OK" if result["achieved_compliance"] else "FAIL"
    print(
        f"\n  RESULT: {result['rounds']}r, {result['total_tokens']:,}t, ${result['total_cost_usd']:.4f}, {ok}"
    )

    # Print comparison if paired
    paired = [
        r
        for r in all_results
        if r["scenario"] == scenario_id and r["trial"] == trial_num
    ]
    if len(paired) == 2:
        w, wo = paired[0], paired[1]
        if w["mode"] == "without":
            w, wo = wo, w
        savings = (
            (1 - w["total_tokens"] / wo["total_tokens"]) * 100
            if wo["total_tokens"]
            else 0
        )
        print(
            f"  SAVINGS: {savings:+.1f}% ({w['total_tokens']:,} vs {wo['total_tokens']:,})"
        )

    return result


if __name__ == "__main__":
    main()
