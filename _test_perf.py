"""Performance benchmarks + correctness validation for Aegis.

Tests:
1. init: time to bootstrap governance on real project
2. check full scan: time + violation count
3. status --json: validity + field correctness
4. staged check: time
5. baseline: time
6. evolve: time
7. Mid-thought validation (code delta): accuracy
8. Rule detection correctness on known patterns
9. CLI output quality assessment
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time


def log(msg: str):
    print(f"  {msg}")
    sys.stdout.flush()


def run(cmd, cwd=None, desc="") -> tuple[int, str, float]:
    start = time.perf_counter()
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=120)
    elapsed = time.perf_counter() - start
    return r.returncode, r.stdout + r.stderr, elapsed


def create_test_project(root: str):
    """Create a test project with known anti-patterns across multiple files."""
    src = os.path.join(root, "src")
    os.makedirs(os.path.join(src, "api"))
    os.makedirs(os.path.join(src, "domain"))
    os.makedirs(os.path.join(src, "infrastructure"))

    # File 1: API handler with multiple violations
    with open(os.path.join(src, "api", "users.py"), "w") as f:
        f.write("""import os
import sys
import json

# TODO: refactor this entire module
def get_user(user_id):
    # FIXME: no auth check
    print(f"Fetching user {user_id}")
    query = f"SELECT * FROM users WHERE id = {user_id}"
    result = eval(query)
    return result

class service:  # should be Service (PascalCase)
    pass

some_value = None
if some_value is not None:
    print(some_value)
""")

    # File 2: Domain service with architecture violations
    with open(os.path.join(src, "domain", "orders.py"), "w") as f:
        f.write("""import os
import sys

from src.infrastructure.database import Database  # domain importing infra = layer violation

_ = "unused value"  # unused variable

class order_service:  # naming violation
    def process(self, data):
        try:  # bare except
            result = data["key"]
        except:
            pass

        items = []
        for i in range(100):
            items.append(i)  # repeated computation pattern
        for i in range(100):
            items.append(i)
        return None  # explicit return None
""")

    # File 3: Infrastructure with security issues
    with open(os.path.join(src, "infrastructure", "database.py"), "w") as f:
        f.write("""import subprocess
import shlex

PASSWORD = "super-secret-123"  # hardcoded password

def run_migration(env):
    cmd = "db-migrate --env " + env  # string formatting injection
    subprocess.call(cmd, shell=True)

def connect(db_name):
    token = "abcdef123456"  # potential secret
    url = f"http://api.example.com/{db_name}"
    return {"connected": True}

import pickle  # unsafe import
""")

    # File 4: Clean file (should have 0 violations)
    with open(os.path.join(src, "api", "clean.py"), "w") as f:
        f.write('"""Clean module with no violations."""\n\nfrom typing import Optional\n\n\ndef process(data: dict) -> Optional[str]:\n    return data.get("key")\n')

    # File 5: Config file (non-Python)
    with open(os.path.join(root, ".env"), "w") as f:
        f.write("SECRET_KEY=should-not-flag\nDEBUG=true\n")

    # File 6: Test file
    test_dir = os.path.join(root, "tests")
    os.makedirs(test_dir)
    with open(os.path.join(test_dir, "test_api.py"), "w") as f:
        f.write('"""Tests for API."""\n\ndef test_get_user():\n    assert True\n')

    # Init git
    subprocess.run(["git", "init"], cwd=root, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True)


def main():
    aegis_root = r"C:\dev\projects\aegis"
    results = {}

    print("=" * 60)
    print("AEGIS PERFORMANCE + CORRECTNESS TEST")
    print("=" * 60)

    # Setup
    test_dir = tempfile.mkdtemp(prefix="aegis_perf_")
    create_test_project(test_dir)

    # =========================================
    # 1. INIT
    # =========================================
    print("\n--- 1. INIT ---")
    log("init: starting...")
    rc, out, elapsed = run(
        ["uv", "run", "aegis", "init"], cwd=test_dir, desc="aegis init"
    )
    results["init_time"] = round(elapsed, 2)
    results["init_rc"] = rc
    log(f"init: {elapsed:.2f}s (rc={rc})")

    # =========================================
    # 2. STATUS
    # =========================================
    print("\n--- 2. STATUS ---")
    rc, out, elapsed = run(
        ["uv", "run", "aegis", "status"], cwd=test_dir, desc="aegis status"
    )
    results["status_time"] = round(elapsed, 2)
    results["status_rc"] = rc
    log(f"status: {elapsed:.2f}s (rc={rc})")

    # Status --json
    rc, out, elapsed = run(
        ["uv", "run", "aegis", "status", "--json"], cwd=test_dir, desc="aegis status --json"
    )
    results["status_json_time"] = round(elapsed, 2)
    results["status_json_rc"] = rc
    if rc == 0:
        try:
            # Extract JSON object from output (stdout + stderr may be mixed)
            json_start = out.index("{")
            json_end = out.rindex("}") + 1
            data = json.loads(out[json_start:json_end])
            results["json_rules_count"] = data.get("rules_count", "?")
            results["json_active_violations"] = data.get("active_violations", "?")
            results["json_engines"] = data.get("engines", {})
            log(f"status --json: {elapsed:.2f}s, rules={data.get('rules_count')}, violations={data.get('active_violations')}")
        except (json.JSONDecodeError, IndexError, ValueError) as e:
            log(f"status --json: PARSE FAILED - {e}")
            results["json_parse_ok"] = False
    else:
        log(f"status --json: FAILED rc={rc}")

    # =========================================
    # 3. CHECK (full scan)
    # =========================================
    print("\n--- 3. CHECK (full scan) ---")

    # First check without timing (auto-baseline will run)
    run(["uv", "run", "aegis", "check"], cwd=test_dir)

    # Clear baseline to get fresh violations for measurement
    baseline_path = os.path.join(test_dir, ".aegis", "baseline.json")
    if os.path.exists(baseline_path):
        os.remove(baseline_path)

    rc, out, elapsed = run(
        ["uv", "run", "aegis", "check", "--exit-code"], cwd=test_dir, desc="aegis check"
    )
    results["check_time"] = round(elapsed, 2)
    results["check_rc"] = rc

    # Parse violations from output
    lines = out.splitlines()
    violation_lines = [l for l in lines if l.strip().startswith("-")]
    results["check_violations_raw"] = len(violation_lines)
    log(f"check: {elapsed:.2f}s, {len(violation_lines)} violations found (rc={rc})")

    # =========================================
    # 4. CHECK --staged
    # =========================================
    print("\n--- 4. CHECK --staged ---")

    # Create a staged change
    with open(os.path.join(src := os.path.join(test_dir, "src"), "api", "users.py"), "a") as f:
        f.write('\nprint("staged change")\n')
    subprocess.run(["git", "add", "src/api/users.py"], cwd=test_dir, capture_output=True)

    rc, out, elapsed = run(
        ["uv", "run", "aegis", "check", "--staged"], cwd=test_dir, desc="aegis check --staged"
    )
    results["check_staged_time"] = round(elapsed, 2)
    results["check_staged_rc"] = rc
    staged_lines = [l for l in out.splitlines() if l.strip().startswith("-")]
    results["check_staged_violations"] = len(staged_lines)
    log(f"check --staged: {elapsed:.2f}s, {len(staged_lines)} violations (rc={rc})")

    # Restore
    subprocess.run(["git", "checkout", "--", "."], cwd=test_dir, capture_output=True)

    # =========================================
    # 5. BASELINE
    # =========================================
    print("\n--- 5. BASELINE ---")
    rc, out, elapsed = run(
        ["uv", "run", "aegis", "baseline"], cwd=test_dir, desc="aegis baseline"
    )
    results["baseline_time"] = round(elapsed, 2)
    results["baseline_rc"] = rc
    log(f"baseline: {elapsed:.2f}s (rc={rc})")

    # =========================================
    # 6. EVOLVE
    # =========================================
    print("\n--- 6. EVOLVE ---")
    rc, out, elapsed = run(
        ["uv", "run", "aegis", "evolve", "arch-no-print", "--action", "suppress", "--rationale", "perf test"],
        cwd=test_dir, desc="aegis evolve"
    )
    results["evolve_time"] = round(elapsed, 2)
    results["evolve_rc"] = rc
    log(f"evolve: {elapsed:.2f}s (rc={rc})")

    # =========================================
    # 7. RULES LIST
    # =========================================
    print("\n--- 7. RULES LIST ---")
    rc, out, elapsed = run(
        ["uv", "run", "aegis", "rules", "list"], cwd=test_dir, desc="aegis rules list"
    )
    results["rules_list_time"] = round(elapsed, 2)
    results["rules_list_rc"] = rc
    log(f"rules list: {elapsed:.2f}s (rc={rc})")

    # =========================================
    # 8. CORRECTNESS: verify violations content
    # =========================================
    print("\n--- 8. CORRECTNESS ANALYSIS ---")

    # Re-run check fresh
    bp = os.path.join(test_dir, ".aegis", "baseline.json")
    if os.path.exists(bp):
        os.remove(bp)

    rc, out, _ = run(
        ["uv", "run", "aegis", "check"], cwd=test_dir
    )

    # Parse rule IDs from violation lines (format: "(rule-id) description")
    import re
    viol_lines = [l.strip() for l in out.splitlines() if l.strip().startswith("-")]
    rule_ids_found = set()
    for vl in viol_lines:
        m = re.match(r".*\(([\w-]+)\)", vl)
        if m:
            rule_ids_found.add(m.group(1))

    # Expected rules given the known anti-patterns in test project files
    expected_rules = {
        "sec-no-eval": "eval(query) in users.py",
        "sec-no-subprocess-shell": "subprocess + shell=True in database.py",
        "sec-no-hardcoded-passwords": 'PASSWORD = "secret" in database.py',
        "bp-explicit-exceptions": "bare except: in orders.py",
        "docs-stale-markers": "TODO/FIXME comments in users.py",
    }

    for rid, desc in expected_rules.items():
        expected_rules[rid] = (desc, rid in rule_ids_found)

    found = sum(1 for _, hit in expected_rules.values() if hit)
    total = len(expected_rules)
    results["correctness_found"] = found
    results["correctness_total"] = total

    log(f"Rule detection: {found}/{total} expected rules fired")
    for rid, (desc, hit) in sorted(expected_rules.items()):
        status = "FIRED" if hit else "MISSED"
        log(f"  [{status}] {rid}: {desc}")

    if viol_lines:
        log(f"\nSample violations (first 5 of {len(viol_lines)}):")
        for vl in viol_lines[:5]:
            log(f"  {vl}")

    # =========================================
    # 9. SUMMARY
    # =========================================
    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    for key, val in sorted(results.items()):
        if "_time" in key:
            op = key.replace("_time", "")
            log(f"  {op:25s} {val}s")
    print()
    for key, val in sorted(results.items()):
        if "_time" not in key:
            log(f"  {key:30s} {val}")

    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)

    return results


if __name__ == "__main__":
    main()
