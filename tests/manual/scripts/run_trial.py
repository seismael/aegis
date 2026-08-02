#!/usr/bin/env python3
"""
Aegis Manual Testing Orchestrator — Python version
Runs trials end-to-end with real agent subprocess calls.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

BASE = Path("C:/dev/projects/aegis")
PROJECT = BASE / "taskflow"
MANUAL = BASE / "tests" / "manual"
PROMPTS_FILE = MANUAL / "prompts.json"
RULES_SRC = BASE / "src" / "aegis" / "resources" / "default_rules"
TRIALS_DIR = MANUAL / "trials"

AGENTS_MD = """# Aegis V4 Governance

You are governed by the Aegis Architectural Microkernel.

## Mandatory Protocol

Before declaring ANY coding task complete, you MUST:
1. Call check_architecture with the list of modified files.
2. If violations are returned, remediate the code natively.
3. Re-run validation until SUCCESS is returned.

Available tools: check_architecture, plan_architecture, fetch_rubric,
init_governance, query_graph, manage_rules, get_scorecard.

Aegis is stateless. Do NOT disable or bypass Aegis governance.
"""

PACK_CONFIG = {
    "L1": ["architecture", "security"],
    "L2": ["architecture", "security", "best-practices", "style", "testing"],
    "L3": [
        "architecture",
        "security",
        "best-practices",
        "style",
        "testing",
        "design",
        "structure",
        "dependencies",
        "documentation",
    ],
    "L4": None,  # all packs
}

NPM_BIN = Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Roaming" / "npm"

AGENT_COMMANDS = {
    "opencode": lambda prompt: [str(NPM_BIN / "opencode.cmd"), "run", prompt],
    "claude": lambda prompt: [str(NPM_BIN / "claude.cmd"), "-p", prompt],
    "aider": lambda prompt: [
        "C:\\Users\\firas\\.local\\bin\\aider.exe",
        "--message",
        prompt,
        "--no-git",
        "--yes",
    ],
    "gemini": lambda prompt: [str(NPM_BIN / "gemini.cmd"), "-p", prompt],
}


def load_prompts():
    with open(PROMPTS_FILE) as f:
        return json.load(f)


def setup_project(mode, rules_level):
    if PROJECT.exists():
        shutil.rmtree(PROJECT)
    shutil.copytree(MANUAL / "projects" / "taskflow", PROJECT)

    # ALWAYS install rules (so we can measure violations in both modes)
    packs = PACK_CONFIG.get(rules_level, [])
    if packs:
        rules_target = PROJECT / ".aegis" / "rules"
        rules_target.mkdir(parents=True, exist_ok=True)
        for pack in packs:
            src = RULES_SRC / pack
            if src.exists():
                shutil.copytree(src, rules_target / pack)

    if mode == "with":
        (PROJECT / "AGENTS.md").write_text(AGENTS_MD, encoding="utf-8")
    else:
        agents_md = PROJECT / "AGENTS.md"
        if agents_md.exists():
            agents_md.unlink()


def run_headless_check(workspace_root=None):
    """Run Aegis headless check using the kernel directly (avoids workspace discovery issues)."""
    ws = str(workspace_root or PROJECT)
    try:
        from aegis.core.baseline import BaselineManager
        from aegis.core.parser import TreeSitterAnalyzer
        from aegis.domain.evaluation.analyzers.graph import GraphAnalyzer
        from aegis.domain.evaluation.analyzers.regex import RegexAnalyzer
        from aegis.domain.evaluation.analyzers.semantic import SemanticAnalyzer
        from aegis.domain.evaluation_service import EvaluationService
        from aegis.domain.policy.parser import PolicyParser

        parser = PolicyParser(ws)
        rules = parser.parse_all()
        if not rules:
            return 0

        evaluation = EvaluationService(
            tree_sitter_analyzer=TreeSitterAnalyzer(),
            graph_analyzer=GraphAnalyzer(),
            regex_analyzer=RegexAnalyzer(),
            semantic_analyzer=SemanticAnalyzer(),
        )
        violations = evaluation.evaluate_workspace(ws, rules)
        baseline = BaselineManager(os.path.join(ws, ".aegis"))
        rule_map = {r.id: r for r in rules}
        active = [
            v for v in violations if not baseline.is_exempt(v, rule_map.get(v.rule_id))
        ]
        return len(active)
    except Exception as e:
        print(f"  [WARN] Headless check failed: {e}")
        return -1


def extract_tokens(output):
    """Try to extract token counts from agent output."""
    tokens = {"input": 0, "output": 0}
    patterns = [
        (r"(\d[\d,]*)\s*input tokens", "input"),
        (r"(\d[\d,]*)\s*tokens?\s*input", "input"),
        (r"(\d[\d,]*)\s*output tokens", "output"),
        (r"(\d[\d,]*)\s*tokens?\s*output", "output"),
        (r"total tokens?.*?(\d[\d,]*)", "total"),
        (r"(\d[\d,]*)\s*total tokens?", "total"),
    ]
    for pattern, key in patterns:
        m = re.search(pattern, output, re.IGNORECASE)
        if m:
            val = int(m.group(1).replace(",", ""))
            if key == "total" and tokens["input"] == 0:
                tokens["input"] = val
            else:
                tokens[key] = val
    return tokens


def count_turns(output):
    count = len(re.findall(r"→|→|Tool|tool_call", output, re.IGNORECASE))
    return max(count, 1)


def run_trial(agent, task, rules_level, mode, run_num):
    prompts = load_prompts()
    prompt_text = prompts.get(task, {}).get("prompt", "")

    trial_id = f"run_{run_num:03d}"
    trial_dir = TRIALS_DIR / trial_id
    trial_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f" TRIAL {trial_id}: {agent} / {task} / {rules_level} / {mode}")
    print(f"{'=' * 60}")

    # Setup
    print(f"  Setting up project ({mode} Aegis, {rules_level} rules)...")
    setup_project(mode, rules_level)

    # Baseline check
    violations_before = run_headless_check()
    print(f"  Violations before: {violations_before}")

    # Run agent
    cmd = AGENT_COMMANDS[agent](prompt_text)
    print(f"  Running: {' '.join(cmd[:3])}...")
    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        output = result.stdout + "\n" + result.stderr
        duration = time.time() - start_time
    except subprocess.TimeoutExpired:
        output = "TIMEOUT after 300s"
        duration = 300
    except Exception as e:
        output = f"ERROR: {e}"
        duration = time.time() - start_time

    # Save output
    output_file = trial_dir / "agent_output.txt"
    output_file.write_text(output, encoding="utf-8")
    output_size = len(output)
    print(f"  Output: {output_size} bytes in {duration:.1f}s")

    # After check
    violations_after = run_headless_check()
    print(f"  Violations after: {violations_after}")

    # Extract metrics
    tokens = extract_tokens(output)
    turns = count_turns(output)

    # Save results
    result = {
        "trial_id": trial_id,
        "agent": agent,
        "task": task,
        "rules": rules_level,
        "mode": mode,
        "run": run_num,
        "started_at": datetime.now().isoformat(),
        "duration_seconds": round(duration, 1),
        "violations_before": violations_before,
        "violations_after": violations_after,
        "input_tokens": tokens["input"],
        "output_tokens": tokens["output"],
        "total_tokens": tokens["input"] + tokens["output"],
        "turns_estimated": turns,
        "output_size_bytes": output_size,
        "prompt_snippet": prompt_text[:100],
    }

    results_file = trial_dir / "result.json"
    results_file.write_text(json.dumps(result, indent=2))
    print(f"  Result: {results_file}")
    return result


def main():
    if len(sys.argv) < 5:
        print(
            "Usage: python run_trial.py <agent> <task> <rules_level> <mode> [run_number]"
        )
        sys.exit(1)

    agent = sys.argv[1]
    task = sys.argv[2]
    rules_level = sys.argv[3]
    mode = sys.argv[4]
    run_num = int(sys.argv[5]) if len(sys.argv) > 5 else 1

    result = run_trial(agent, task, rules_level, mode, run_num)
    v_before = result["violations_before"]
    v_after = result["violations_after"]
    print(f"\n  DONE - violations: {v_before} -> {v_after}")
    print(f"  Tokens: in={result['input_tokens']} out={result['output_tokens']}")


if __name__ == "__main__":
    main()
