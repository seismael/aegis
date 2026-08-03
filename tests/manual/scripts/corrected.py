#!/usr/bin/env python3
"""
Aegis Token Efficiency — CORRECTED Comparison

Fixes all 5 flaws from previous version:
  Fix #1: plan output fed INTO gen prompt (not discarded)
  Fix #2: in-process rule lookup (no LLM cost for plan_architecture)
  Fix #3: starts from 0 baseline (fixes seeded violations first)
  Fix #4: single API call per round (rules are prompt text, not separate call)
  Fix #5: validates token JSON, logs errors

WITH: gen_prompt = "Rules: [in-process plan output]\n\nTask: [feature]"
WITHOUT: gen_prompt = "Task: [feature]"
Both paths: single Claude call + headless check + retry loop
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
CLAUDE = str(NPM_BIN / "claude.cmd")
RESULTS_FILE = MANUAL / "results" / "corrected.json"

CORE_PACKS = ["architecture", "security", "best-practices"]


def setup_project():
    for _attempt in range(3):
        if PROJECT.exists():
            try:
                shutil.rmtree(PROJECT)
            except (PermissionError, OSError):
                import gc

                gc.collect()
                time.sleep(3)
                try:
                    shutil.rmtree(PROJECT)
                except (PermissionError, OSError):
                    subprocess.run(
                        ["cmd", "/c", "rmdir", "/s", "/q", str(PROJECT)], timeout=15
                    )
                    time.sleep(3)
        if not PROJECT.exists():
            break
    shutil.copytree(MANUAL / "projects" / "taskflow", PROJECT, dirs_exist_ok=True)
    rules_target = PROJECT / ".aegis" / "rules"
    rules_target.mkdir(parents=True, exist_ok=True)
    for pack in CORE_PACKS:
        src = RULES_SRC / pack
        if src.exists():
            shutil.copytree(src, rules_target / pack)


def get_rules_for_files(file_paths):
    """In-process rule lookup — no LLM cost."""
    sys.path.insert(0, str(BASE / "src"))
    from aegis.core.scoping import ScopeFilter
    from aegis.domain.policy.parser import PolicyParser

    parser = PolicyParser(str(PROJECT))
    rules = parser.parse_all()
    if not rules:
        return "No rules apply."
    relevant = ScopeFilter.filter_rules_for_files(file_paths, rules, max_rules=20)
    lines = []
    for r in relevant:
        lines.append(f"    {r.id} [{r.severity.value}]: {r.description}")
        if r.rationale:
            lines.append(f"      Rationale: {r.rationale}")
    return "\n".join(lines) if lines else "No rules apply."


def clean_baseline_violations():
    """Fix seeded violations by patching files directly — no Claude call needed."""
    print("  Cleaning baseline violations...")

    # Fix api/routes.py — remove exec() call
    routes = (PROJECT / "api" / "routes.py").read_text(encoding="utf-8")
    routes = routes.replace(
        "    exec(f\"global_{user_input} = '{title}'\")",
        '    import logging; logging.warning(f"Debug eval disabled: {user_input}")',
    )
    (PROJECT / "api" / "routes.py").write_text(routes, encoding="utf-8")

    # Fix application/use_cases.py — remove hardcoded password
    use_cases = (PROJECT / "application" / "use_cases.py").read_text(encoding="utf-8")
    use_cases = use_cases.replace(
        'password = "admin123"', 'password = os.environ.get("ADMIN_PASSWORD", "")'
    )
    use_cases = use_cases.replace(
        "from domain.models import Task, User",
        "import os\nfrom domain.models import Task, User",
    )
    (PROJECT / "application" / "use_cases.py").write_text(use_cases, encoding="utf-8")

    # Fix domain/services.py — replace bare except with specific exception
    svc = (PROJECT / "domain" / "services.py").read_text(encoding="utf-8")
    svc = svc.replace(
        "            except:\n                pass",
        "            except Exception:\n                pass",
    )
    (PROJECT / "domain" / "services.py").write_text(svc, encoding="utf-8")

    violations, _ = run_headless_check()
    print(f"    After cleanup: {violations} violations")
    return violations == 0


def run_headless_check():
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
        if inp == 0 and out == 0:
            print(f"    WARN: parse_tokens returned zeros — output: {output[:200]}")
        return {
            "input": inp,
            "output": out,
            "total": inp + out,
            "turns": d.get("num_turns", 0),
            "cost": d.get("total_cost_usd", 0),
        }
    except json.JSONDecodeError:
        print(f"    WARN: parse_tokens JSONDecodeError — output: {output[:200]}")
        return {"input": 0, "output": 0, "total": 0, "turns": 0, "cost": 0}


def load_scenarios():
    return json.loads((MANUAL / "prompts.json").read_text())


def run_scenario(scenario_id, mode, trial_num):
    sc = load_scenarios()[scenario_id]
    setup_project()

    # Fix #3: clean baseline — direct file patching, zero LLM cost
    ok = clean_baseline_violations()
    violations_before, _ = run_headless_check()
    if not ok or violations_before != 0:
        print(
            f"  ERROR: Could not clean baseline ({violations_before} violations remain)"
        )
        return None
    print(f"  Baseline: {violations_before}")

    # Fix #2 + #4: in-process rules, single call WITH
    rules_text = ""
    if mode == "with":
        rules_text = get_rules_for_files(sc["files"])
        print(f"  Rules injected ({len(rules_text)} chars)")

    rounds_data = []
    violations_now = 0
    v_list = []

    for rnd in range(1, 6):
        if rnd == 1:
            if mode == "with":
                prompt = (
                    f"Architectural rules for the files you are modifying:\n\n"
                    f"{rules_text}\n\n"
                    f"Follow ALL of these rules.\n\n"
                    f"Task: {sc['prompt']}"
                )
            else:
                prompt = sc["prompt"]
        else:
            prompt = "Fix these architectural violations:\n"
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
