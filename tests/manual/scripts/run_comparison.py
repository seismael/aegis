#!/usr/bin/env python3
"""
Aegis Token Efficiency — Corrected Comparison
WITH: plan_architecture(files) → informed generation → check_architecture
WITHOUT: blind generation → check_architecture
Both paths run check_architecture after code. Both measured to 0 violations.
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
RESULTS_FILE = MANUAL / "results" / "comparison.json"

CORE_PACKS = ["architecture", "security", "best-practices"]

CLAUDE_MD = (
    "# Aegis V4 Governance\n"
    "You have access to the aegis-kernel MCP server.\n"
    "Before generating any code, call plan_architecture with the files you intend to modify.\n"
    "After generating code, call check_architecture with those files.\n"
    "If violations are found, fix them and re-check.\n"
    "Do NOT declare the task complete until check_architecture returns SUCCESS.\n"
)


def load_scenarios():
    return json.loads((MANUAL / "prompts.json").read_text())


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
        (PROJECT / "CLAUDE.md").write_text(CLAUDE_MD, encoding="utf-8")
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


def run_headless_check():
    import sys as _sys

    _sys.path.insert(0, str(BASE / "src"))
    from aegis.core.baseline import BaselineManager
    from aegis.core.parser import TreeSitterAnalyzer
    from aegis.domain.evaluation.analyzers.graph import GraphAnalyzer
    from aegis.domain.evaluation.analyzers.regex import RegexAnalyzer
    from aegis.domain.evaluation.analyzers.semantic import SemanticAnalyzer
    from aegis.domain.evaluation_service import EvaluationService
    from aegis.domain.policy.parser import PolicyParser

    ws = str(PROJECT)
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


def call_claude(prompt):
    cmd = [
        CLAUDE_CMD,
        "-p",
        "--output-format",
        "json",
        "--dangerously-skip-permissions",
        prompt,
    ]
    start = time.time()
    try:
        r = subprocess.run(
            cmd,
            cwd=str(PROJECT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        return r.stdout, time.time() - start
    except subprocess.TimeoutExpired:
        return '{"error":"timeout"}', 600
    except Exception as e:
        return f'{{"error":"{e}"}}', time.time() - start


def parse_tokens(output):
    try:
        d = json.loads(output)
        u = d.get("usage", {})
        return {
            "input": u.get("input_tokens", 0),
            "output": u.get("output_tokens", 0),
            "total": u.get("input_tokens", 0) + u.get("output_tokens", 0),
            "turns": d.get("num_turns", 0),
            "cost": d.get("total_cost_usd", 0),
        }
    except json.JSONDecodeError:
        return {"input": 0, "output": 0, "total": 0, "turns": 0, "cost": 0}


def run_scenario(scenario_id, mode, trial_num):
    sc = load_scenarios()[scenario_id]
    setup_project(mode)

    violations_before, _ = run_headless_check()
    print(f"\n{'=' * 60}")
    print(f" {scenario_id}: {sc['name']} [{mode.upper()}] Trial {trial_num}")
    print(f"{'=' * 60}")
    print(f"  Baseline violations: {violations_before}")

    rounds_data = []
    violations_now = violations_before
    v_list = []

    for rnd in range(1, 6):
        rnd_tokens = {"input": 0, "output": 0, "total": 0, "turns": 0, "cost": 0}

        if rnd == 1 and mode == "with":
            # STEP A: plan_architecture before code generation
            files_str = ", ".join(sc["files"])
            plan_prompt = (
                f"I need to modify these files: {files_str}.\n"
                "Call the plan_architecture tool for these files.\n"
                "Show me ALL the architecture rules that apply to these files.\n"
                "Return the full output."
            )
            plan_output, plan_wt = call_claude(plan_prompt)
            plan_tk = parse_tokens(plan_output)
            rnd_tokens = {
                "input": rnd_tokens["input"] + plan_tk["input"],
                "output": rnd_tokens["output"] + plan_tk["output"],
                "total": rnd_tokens["total"] + plan_tk["total"],
                "turns": rnd_tokens["turns"] + plan_tk["turns"],
                "cost": round(rnd_tokens["cost"] + plan_tk["cost"], 4),
            }
            print(f"    Plan: {plan_tk['total']:,}t [{plan_wt:.0f}s]")

            # STEP B: informed code generation
            gen_prompt = sc["prompt"]
            gen_output, gen_wt = call_claude(gen_prompt)
            gen_tk = parse_tokens(gen_output)
            rnd_tokens = {
                "input": rnd_tokens["input"] + gen_tk["input"],
                "output": rnd_tokens["output"] + gen_tk["output"],
                "total": rnd_tokens["total"] + gen_tk["total"],
                "turns": rnd_tokens["turns"] + gen_tk["turns"],
                "cost": round(rnd_tokens["cost"] + gen_tk["cost"], 4),
            }
            print(f"    Gen:  {gen_tk['total']:,}t [{gen_wt:.0f}s]")
        elif rnd == 1:
            # WITHOUT: just generate
            gen_output, gen_wt = call_claude(sc["prompt"])
            gen_tk = parse_tokens(gen_output)
            rnd_tokens = gen_tk
            print(f"    Gen:  {gen_tk['total']:,}t [{gen_wt:.0f}s]")
        else:
            # Retry round (both modes)
            retry_prompt = "Fix these architectural violations:\n"
            for v in v_list[:10]:
                retry_prompt += f"  - {v.file}:{v.line} [{v.rule_id}] {v.description}\n"
            retry_output, retry_wt = call_claude(retry_prompt)
            retry_tk = parse_tokens(retry_output)
            rnd_tokens = retry_tk
            print(f"    Fix:  {retry_tk['total']:,}t [{retry_wt:.0f}s]")

        violations_now, v_list = run_headless_check()
        status = "CLEAN" if violations_now == 0 else f"{violations_now} left"
        print(f"    R{rnd}: {rnd_tokens['total']:,}t | {status}")

        rounds_data.append(
            {
                "round": rnd,
                "tokens": rnd_tokens,
                "violations_after": violations_now,
            }
        )

        if violations_now == 0:
            break

    result = {
        "scenario": scenario_id,
        "name": sc["name"],
        "mode": mode,
        "trial": trial_num,
        "violations_before": violations_before,
        "violations_after": violations_now,
        "rounds": len(rounds_data),
        "total_tokens": sum(r["tokens"]["total"] for r in rounds_data),
        "total_input_tokens": sum(r["tokens"]["input"] for r in rounds_data),
        "total_output_tokens": sum(r["tokens"]["output"] for r in rounds_data),
        "total_cost": round(sum(r["tokens"]["cost"] for r in rounds_data), 4),
        "total_turns": sum(r["tokens"]["turns"] for r in rounds_data),
        "achieved_compliance": violations_now == 0,
        "detail": rounds_data,
    }

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    all_results = json.loads(RESULTS_FILE.read_text()) if RESULTS_FILE.exists() else []
    all_results.append(result)
    RESULTS_FILE.write_text(json.dumps(all_results, indent=2))

    print(
        f"  TOTAL: {result['total_tokens']:,}t, {result['rounds']}r, ${result['total_cost']:.4f}"
    )
    return result


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "with"
    scenario_id = sys.argv[2] if len(sys.argv) > 2 else "S1"
    trial_num = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    run_scenario(scenario_id, mode, trial_num)
