#!/usr/bin/env python3
"""
Aegis Systematic Testing — Runs all agents, captures real token counts, violations.
With/without Aegis paired comparison.
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
PROMPTS_FILE = MANUAL / "prompts.json"
RULES_SRC = BASE / "src" / "aegis" / "resources" / "default_rules"
TRIALS_DIR = MANUAL / "trials"
MCP_WRAPPER = MANUAL / "scripts" / "aegis-mcp.cmd"

AGENTS_MD = """# Aegis V4 Governance
You are governed by the Aegis Architectural Microkernel.
Before declaring ANY coding task complete, you MUST:
1. Call check_architecture with the list of modified files.
2. If violations are returned, remediate the code natively.
3. Re-run validation until SUCCESS is returned.
Available tools: check_architecture, plan_architecture, fetch_rubric, init_governance, query_graph, manage_rules, get_scorecard.
Do NOT disable or bypass Aegis governance for any reason.
"""

PACK_CONFIG = {
    "L2": ["architecture", "security", "best-practices", "style", "testing"],
}

NPM_BIN = Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Roaming" / "npm"

AGENT_CMDS = {
    "claude": lambda prompt: [
        str(NPM_BIN / "claude.cmd"),
        "-p",
        "--output-format",
        "json",
        "--dangerously-skip-permissions",
        prompt,
    ],
    "gemini": lambda prompt: [
        str(NPM_BIN / "gemini.cmd"),
        "-p",
        prompt,
        "--output-format",
        "json",
        "--approval-mode",
        "yolo",
    ],
}


def setup_project(mode, packs):
    if PROJECT.exists():
        shutil.rmtree(PROJECT)
    shutil.copytree(MANUAL / "projects" / "taskflow", PROJECT)

    if mode == "with":
        rules_target = PROJECT / ".aegis" / "rules"
        rules_target.mkdir(parents=True, exist_ok=True)
        for pack in packs:
            src = RULES_SRC / pack
            if src.exists():
                shutil.copytree(src, rules_target / pack)

        # Create CLAUDE.md for Claude Code
        (PROJECT / "CLAUDE.md").write_text(AGENTS_MD, encoding="utf-8")
        # Create AGENTS.md for opencode/gemini
        (PROJECT / "AGENTS.md").write_text(AGENTS_MD, encoding="utf-8")

        # Create MCP config in .aegis/
        mcp_config = {
            "mcpServers": {
                "aegis-kernel": {
                    "command": str(MCP_WRAPPER),
                    "args": [],
                }
            }
        }
        mcp_json = PROJECT / ".aegis" / "mcp.json"
        mcp_json.write_text(json.dumps(mcp_config, indent=2))

        # Register MCP server with Claude Code for this trial
        subprocess.run(
            [
                str(NPM_BIN / "claude.cmd"),
                "mcp",
                "add",
                "aegis-kernel",
                "--",
                str(MCP_WRAPPER),
            ],
            cwd=str(PROJECT),
            capture_output=True,
            timeout=15,
        )
    else:
        # Remove all governance
        for path in [
            PROJECT / ".aegis",
            PROJECT / "CLAUDE.md",
            PROJECT / "AGENTS.md",
            PROJECT / "GEMINI.md",
        ]:
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()

        # Remove Aegis MCP from Claude global config
        subprocess.run(
            [str(NPM_BIN / "claude.cmd"), "mcp", "remove", "aegis-kernel"],
            capture_output=True,
            timeout=10,
        )


def run_headless_check():
    try:
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
    except Exception:
        return -1


def run_trial(agent, mode, run_num):
    packs = PACK_CONFIG["L2"]
    prompt_text = load_prompt("T2")
    trial_id = f"run_{run_num:03d}"
    trial_dir = TRIALS_DIR / trial_id
    trial_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 60}")
    print(f" TRIAL {trial_id}: {agent} / T2 / L2 / {mode}")
    print(f"{'=' * 60}")

    # Setup
    setup_project(mode, packs)
    violations_before = run_headless_check()
    print(f"  Violations before: {violations_before}")

    # Run agent
    cmd = AGENT_CMDS[agent](prompt_text)
    print(f"  Running: {cmd[0]} (non-interactive, {mode} Aegis)...")
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
        duration = time.time() - start
        output = result.stdout
    except subprocess.TimeoutExpired:
        output = '{"error": "timeout"}'
        duration = 600
    except Exception as e:
        output = f'{{"error": "{e}"}}'
        duration = time.time() - start

    output_file = trial_dir / "agent_output.json"
    output_file.write_text(output, encoding="utf-8")

    # Parse JSON for token counts
    tokens = {
        "input": 0,
        "output": 0,
        "total": 0,
        "turns": 0,
        "duration_ms": 0,
        "cost": 0,
    }
    try:
        data = json.loads(output)
        usage = data.get("usage", {})
        tokens["input"] = usage.get("input_tokens", 0)
        tokens["output"] = usage.get("output_tokens", 0)
        tokens["total"] = tokens["input"] + tokens["output"]
        tokens["turns"] = data.get("num_turns", 0)
        tokens["duration_ms"] = data.get("duration_ms", 0)
        tokens["cost"] = data.get("total_cost_usd", 0)
    except json.JSONDecodeError:
        pass

    # Violations after
    violations_after = run_headless_check()
    print(f"  Violations after: {violations_after}")

    # Save result
    result = {
        "trial_id": trial_id,
        "agent": agent,
        "mode": mode,
        "violations_before": violations_before,
        "violations_after": violations_after,
        "input_tokens": tokens["input"],
        "output_tokens": tokens["output"],
        "total_tokens": tokens["total"],
        "turns": tokens["turns"],
        "duration_ms": tokens["duration_ms"],
        "cost_usd": tokens["cost"],
        "wall_seconds": round(duration, 1),
    }
    (trial_dir / "result.json").write_text(json.dumps(result, indent=2))

    print(
        f"  Tokens: {tokens['input']} in + {tokens['output']} out = {tokens['total']} total"
    )
    print(f"  Turns: {tokens['turns']}, Cost: ${tokens['cost']:.4f}")
    print(f"  Violations: {violations_before} -> {violations_after}")

    return result


def load_prompt(task_id):
    with open(PROMPTS_FILE) as f:
        return json.load(f)[task_id]["prompt"]


def main():
    agent = sys.argv[1] if len(sys.argv) > 1 else "claude"
    run_num = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    # WITH Aegis
    r1 = run_trial(agent, "with", run_num)

    # WITHOUT Aegis
    r2 = run_trial(agent, "without", run_num + 1)

    # Compare
    if r1["total_tokens"] > 0 and r2["total_tokens"] > 0:
        savings = (1 - r1["total_tokens"] / r2["total_tokens"]) * 100
        print(f"\n{'=' * 60}")
        print(f" TOKEN EFFICIENCY: {agent}")
        print(f"{'=' * 60}")
        print(
            f"  WITH Aegis:     {r1['total_tokens']:,} tokens ({r1['turns']} turns) ${r1['cost_usd']:.4f}"
        )
        print(
            f"  WITHOUT Aegis:  {r2['total_tokens']:,} tokens ({r2['turns']} turns) ${r2['cost_usd']:.4f}"
        )
        print(f"  Savings:        {savings:+.1f}%")
        print(
            f"  Violation delta WITH:    {r1['violations_before']}->{r1['violations_after']}"
        )
        print(
            f"  Violation delta WITHOUT: {r2['violations_before']}->{r2['violations_after']}"
        )
    else:
        print("No token data to compare.")


if __name__ == "__main__":
    main()
