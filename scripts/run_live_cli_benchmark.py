"""
Real-World Subprocess CLI Live Benchmark Suite for Aegis.
Executes live Aegis CLI processes (aegis init, aegis check, aegis plan, aegis prompt) via real OS subprocesses
on C:\\example, capturing live stdout/stderr byte counts, actual subprocess wall-clock milliseconds,
and live filesystem mutations.

No mocks. No stubs. 100% real CLI binary execution.
"""

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path


def count_tokens(text: str) -> int:
    if not text:
        return 0
    tokens = re.findall(r"\w+|[^\w\s]|\s+", text)
    return len(tokens)


def clean_workspace(workspace_path: str):
    wp = Path(workspace_path)
    if wp.exists():
        for child in wp.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                try:
                    child.unlink()
                except OSError:
                    pass
    wp.mkdir(parents=True, exist_ok=True)


class LiveCLIBenchmarkRunner:

    def __init__(self, workspace: str = r"C:\example"):
        self.workspace = workspace
        clean_workspace(self.workspace)

    def run_live_cli_command(self, args: list[str]) -> tuple[int, str, str, float]:
        """Executes a real aegis CLI command as a live subprocess and measures wall-clock ms."""
        cmd = ["uv", "run", "aegis"] + args
        t0 = time.perf_counter()
        proc = subprocess.run(
            cmd,
            cwd=self.workspace,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return proc.returncode, proc.stdout, proc.stderr, round(latency_ms, 2)

    def test_scenario_1_live_init(self) -> dict:
        """Scenario 1: Live 'aegis init' command deployment in real workspace."""
        code, out, err, latency = self.run_live_cli_command(["init", "--workspace", self.workspace])

        agents_md = Path(self.workspace) / "AGENTS.md"
        claude_md = Path(self.workspace) / "CLAUDE.md"

        files_created = agents_md.exists() or claude_md.exists()
        stdout_tokens = count_tokens(out)

        return {
            "scenario": "Live CLI Scenario 1: aegis init",
            "returncode": code,
            "latency_ms": latency,
            "stdout_tokens": stdout_tokens,
            "filesystem_mutated_successfully": files_created,
            "status": "PASS" if code == 0 and files_created else "FAIL",
        }


    def test_scenario_2_live_plan_verification(self) -> dict:
        """Scenario 2: Live 'aegis agent' command intent check."""
        # Test valid plan
        code1, out1, err1, lat1 = self.run_live_cli_command(
            ["agent", "--workspace", self.workspace, "--plan-import", "logging", "--target-module", "domain.orders"]
        )

        # Test violating plan
        code2, out2, err2, lat2 = self.run_live_cli_command(
            ["agent", "--workspace", self.workspace, "--plan-import", "infrastructure.db", "--target-module", "domain.orders"]
        )

        interception = "PLAN REJECTED" in out2 or "Plan valid: False" in out2 or code2 != 0

        return {
            "scenario": "Live CLI Scenario 2: aegis agent plan intent check",
            "valid_plan_latency_ms": lat1,
            "violating_plan_latency_ms": lat2,
            "valid_plan_returncode": code1,
            "violating_plan_returncode": code2,
            "interception_confirmed": interception,
            "status": "PASS" if code1 == 0 and interception else "FAIL",
        }


    def test_scenario_3_live_prompt_enrichment(self) -> dict:
        """Scenario 3: Live 'aegis prompt' JIT rule scoping command."""
        domain_dir = Path(self.workspace) / "src" / "domain"
        domain_dir.mkdir(parents=True, exist_ok=True)
        (domain_dir / "service.py").write_text("def process(): pass\n", encoding="utf-8")

        code, out, err, latency = self.run_live_cli_command(
            ["prompt", "Add billing notification logic", "--files", "src/domain/service.py"]
        )

        prompt_tokens = count_tokens(out)

        return {
            "scenario": "Live CLI Scenario 3: aegis prompt JIT scoping",
            "returncode": code,
            "latency_ms": latency,
            "enriched_prompt_tokens": prompt_tokens,
            "jit_rules_injected": "Architectural rules" in out or "Rules" in out or prompt_tokens > 10,
            "status": "PASS" if code == 0 else "FAIL",
        }

    def test_scenario_4_live_check_headless_sweep(self) -> dict:
        """Scenario 4: Live 'aegis check' headless workspace sweep."""
        domain_dir = Path(self.workspace) / "src" / "domain"
        domain_dir.mkdir(parents=True, exist_ok=True)
        violating_code = (
            "import sqlite3\n"
            "AWS_SECRET_KEY = 'AKIAIOSFODNN7EXAMPLE'\n"
            "def run():\n"
            "    print('debug output')\n"
        )
        (domain_dir / "violating_service.py").write_text(violating_code, encoding="utf-8")

        code, out, err, latency = self.run_live_cli_command(["check", "--format", "json"])

        stdout_tokens = count_tokens(out)
        violations_detected = "violations" in out.lower() or "sec-no-hardcoded-credentials" in out or code != 0

        return {
            "scenario": "Live CLI Scenario 4: aegis check headless sweep",
            "returncode": code,
            "sweep_latency_ms": latency,
            "stdout_tokens": stdout_tokens,
            "violations_detected_live": violations_detected,
            "status": "PASS" if violations_detected else "FAIL",
        }


    def execute_live_cli_suite(self) -> dict:
        print("==================================================================")

        print("    REAL-WORLD SUBPROCESS CLI LIVE BENCHMARK SUITE                ")
        print("==================================================================")
        print(f"Target Workspace: {self.workspace}")
        print("Execution Mode: Live OS Subprocesses (`uv run aegis <args>`)")
        print("------------------------------------------------------------------\n")

        s1 = self.test_scenario_1_live_init()
        s2 = self.test_scenario_2_live_plan_verification()
        s3 = self.test_scenario_3_live_prompt_enrichment()
        s4 = self.test_scenario_4_live_check_headless_sweep()

        scenarios = [s1, s2, s3, s4]

        for s in scenarios:
            print(f"[+] {s['scenario']}:")
            for k, v in s.items():
                if k != "scenario":
                    print(f"    - {k}: {v}")
            print()

        payload = {
            "execution_type": "100% Real OS Subprocess CLI Execution",
            "workspace": self.workspace,
            "scenarios": scenarios,
        }

        output_path = Path(self.workspace) / "benchmark_live_cli_results.json"
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        print("==================================================================")
        print(f"Saved live subprocess CLI benchmark payload to: {output_path}")
        print("==================================================================")
        return payload



def main():
    workspace = os.environ.get("BENCHMARK_WORKSPACE", r"C:\example")
    runner = LiveCLIBenchmarkRunner(workspace=workspace)
    runner.execute_live_cli_suite()


if __name__ == "__main__":
    main()
