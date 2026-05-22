"""Targeted correctness test: verify security rules fire against known patterns."""
import os
import subprocess
import sys
import tempfile

TEST_FILES = {
    "src/api/users.py": """import os
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
""",
    "src/domain/orders.py": """import os
import sys

from src.infrastructure.database import Database

_ = "unused value"

class order_service:
    def process(self, data):
        try:
            result = data["key"]
        except:
            pass

        items = []
        for i in range(100):
            items.append(i)
        for i in range(100):
            items.append(i)
        return None
""",
    "src/infrastructure/database.py": """import subprocess
import shlex

PASSWORD = "super-secret-123"

def run_migration(env):
    cmd = "db-migrate --env " + env
    subprocess.call(cmd, shell=True)

def connect(db_name):
    token = "abcdef123456"
    url = f"http://api.example.com/{db_name}"
    return {"connected": True}

import pickle
""",
    "src/api/clean.py": '"""Clean module with no violations."""\n\ndef process(data: dict) -> str:\n    return data.get("key")\n',
}

EXPECTED_RULES = {
    "sec-no-eval": {"file": "users.py", "reason": "eval(query)"},
    "sec-no-subprocess-shell": {"file": "database.py", "reason": "subprocess.call(cmd, shell=True)"},
    "sec-no-hardcoded-passwords": {"file": "database.py", "reason": 'PASSWORD = "super-secret-123"'},
    "arch-no-todo": {"file": "users.py", "reason": "# TODO comment"},
    "arch-layer-violation": {"file": "orders.py", "reason": "domain imports infrastructure"},
    "bp-explicit-exceptions": {"file": "orders.py", "reason": "bare except:"},
    "style-naming-convention": {"file": "orders.py", "reason": "class order_service (snake_case)"},
    "docs-module-docstring": {"file": "users.py", "reason": "no module docstring"},
}


def main():
    root = tempfile.mkdtemp(prefix="aegis_correctness_")
    print(f"Test project: {root}")

    # Create files
    for path, content in TEST_FILES.items():
        full = os.path.join(root, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)

    # Init git
    subprocess.run(["git", "init"], cwd=root, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=root, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True)

    aegis_root = r"C:\dev\projects\aegis"

    # Init governance
    r = subprocess.run(["uv", "run", "aegis", "init"], cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"INIT FAILED: {r.stderr}")
        return 1

    # Run check — capture both stdout and stderr
    r = subprocess.run(["uv", "run", "aegis", "check"], cwd=root, capture_output=True, text=True)
    output = r.stdout
    errors = r.stderr

    # Parse violation lines
    viol_lines = [l.strip() for l in output.splitlines() if l.strip().startswith("-")]
    viol_rules = set()
    file_rules = {}
    for vl in viol_lines:
        # Parse: - MODE file:line (rule-id)
        if "(" in vl and ")" in vl:
            rule_id = vl.split("(")[-1].split(")")[0]
            viol_rules.add(rule_id)
            # Also track per file
            parts = vl.split()
            if len(parts) >= 3:
                fname = parts[1].split(":")[0]
                file_rules.setdefault(fname, set()).add(rule_id)

    print(f"\n{'='*60}")
    print(f"CORRECTNESS RESULTS: {len(viol_rules)} unique rules fired, {len(viol_lines)} total violations")
    print(f"{'='*60}")

    results = {}
    for rule_id, expected in EXPECTED_RULES.items():
        found = rule_id in viol_rules
        results[rule_id] = found
        status = "PASS" if found else "FAIL"
        print(f"  [{status}] {rule_id:40s} expected in {expected['file']:15s} ({expected['reason']})")

    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n  Score: {passed}/{total}")

    # If failures, show what's missing
    missing = [rid for rid, found in results.items() if not found]
    if missing:
        print(f"\n  MISSING RULES: {', '.join(missing)}")
        print(f"\n  All {len(viol_rules)} fired rules:")
        for rid in sorted(viol_rules):
            print(f"    - {rid}")
        print("\n  Per-file breakdown:")
        for fname, rules in sorted(file_rules.items()):
            print(f"    {fname}:")
            for rid in sorted(rules):
                print(f"      - {rid}")

    # Cleanup
    import shutil
    shutil.rmtree(root, ignore_errors=True)

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
