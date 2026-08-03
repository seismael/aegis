#!/usr/bin/env python3
"""
Aegis Native Token Efficiency — Uses REAL aegis init + MCP tools.
WITH: aegis init → AGENTS.md + MCP + rules → agent calls check_architecture
WITHOUT: no Aegis traces → agent is blind
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
NPM_BIN = Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Roaming" / "npm"
CLAUDE = str(NPM_BIN / "claude.cmd")
RESULTS_FILE = MANUAL / "results" / "native.json"


def setup_project(mode):
    if PROJECT.exists():
        for _ in range(3):
            try:
                shutil.rmtree(PROJECT)
            except (PermissionError, OSError):
                import gc

                gc.collect()
                time.sleep(3)
            else:
                break
    shutil.copytree(MANUAL / "projects" / "taskflow", PROJECT, dirs_exist_ok=True)

    if mode == "with":
        subprocess.run(
            ["aegis", "init", "--tool", "claude"],
            cwd=str(PROJECT),
            capture_output=True,
            timeout=30,
        )
        # Register MCP for this trial
        subprocess.run(
            [CLAUDE, "mcp", "add", "aegis-kernel", "--", "uvx", "aegis", "run"],
            capture_output=True,
            timeout=15,
        )
    else:
        for path in [
            PROJECT / ".aegis",
            PROJECT / "AGENTS.md",
            PROJECT / "CLAUDE.md",
            PROJECT / "GEMINI.md",
        ]:
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink(missing_ok=True)
        subprocess.run(
            [CLAUDE, "mcp", "remove", "aegis-kernel"],
            capture_output=True,
            timeout=10,
        )


def run_headless_check():
    sys.path.insert(0, str(BASE / "src"))
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
    ev = EvaluationService(
        TreeSitterAnalyzer(), GraphAnalyzer(), RegexAnalyzer(), SemanticAnalyzer()
    )
    violations = ev.evaluate_workspace(ws, rules)
    baseline = BaselineManager(os.path.join(ws, ".aegis"))
    rm = {r.id: r for r in rules}
    active = [v for v in violations if not baseline.is_exempt(v, rm.get(v.rule_id))]
    return len(active), active


def call_claude(prompt):
    cmd = [
        CLAUDE,
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
        inp = u.get("input_tokens", 0)
        out = u.get("output_tokens", 0)
        return {
            "input": inp,
            "output": out,
            "total": inp + out,
            "turns": d.get("num_turns", 0),
            "cost": d.get("total_cost_usd", 0),
        }
    except json.JSONDecodeError:
        return {"input": 0, "output": 0, "total": 0, "turns": 0, "cost": 0}


def load_scenarios():
    return json.loads((MANUAL / "prompts.json").read_text())


def run_scenario(scenario_id, mode, trial_num):
    sc = load_scenarios()[scenario_id]
    setup_project(mode)

    violations_before, _ = run_headless_check()
    print(f"\n{'=' * 60}")
    print(f" {scenario_id}: {sc['name']} [{mode.upper()}] Trial {trial_num}")
    print(f"  Baseline violations: {violations_before}")

    rounds_data = []
    violations_now = violations_before
    v_list = []

    for rnd in range(1, 6):
        if rnd == 1:
            prompt = sc["prompt"]
        else:
            prompt = "Fix these violations:\n"
            for v in v_list[:10]:
                prompt += f"  - {v.file}:{v.line} [{v.rule_id}] {v.description}\n"

        output, wall_time = call_claude(prompt)
        tokens = parse_tokens(output)
        violations_now, v_list = run_headless_check()
        status = "CLEAN" if violations_now == 0 else f"{violations_now} left"
        print(f"    R{rnd}: {tokens['total']:,}t [{wall_time:.0f}s] | {status}")

        rounds_data.append(
            {
                "round": rnd,
                "tokens": tokens,
                "wall_seconds": round(wall_time, 1),
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
        "total_cost": round(sum(r["tokens"]["cost"] for r in rounds_data), 4),
        "achieved_compliance": violations_now == 0,
        "detail": rounds_data,
    }

    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(RESULTS_FILE.read_text()) if RESULTS_FILE.exists() else []
    existing.append(result)
    RESULTS_FILE.write_text(json.dumps(existing, indent=2))

    print(
        f"  TOTAL: {result['total_tokens']:,}t, {result['rounds']}r, ${result['total_cost']:.4f}"
    )
    return result


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "with"
    scenario_id = sys.argv[2] if len(sys.argv) > 2 else "S1"
    trial_num = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    run_scenario(scenario_id, mode, trial_num)
