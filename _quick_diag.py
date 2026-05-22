"""Quick diagnostics for identified failures."""
import json
import os
import shutil
import subprocess
import tempfile


def run(cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=30)
    return r.returncode, r.stdout, r.stderr

root = tempfile.mkdtemp(prefix="aegis_diag_")
print(f"Test project: {root}")

os.makedirs(os.path.join(root, "src"))
with open(os.path.join(root, "src", "test.py"), "w") as f:
    f.write('import os\nPASSWORD = "test123"\neval("print(1)")\n')
with open(os.path.join(root, "src", "clean.py"), "w") as f:
    f.write('"""Clean."""\nx = 1\n')

subprocess.run(["git", "init"], cwd=root, capture_output=True)
subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=root, capture_output=True)
subprocess.run(["git", "config", "user.name", "t"], cwd=root, capture_output=True)
subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True)

# 1. Init
rc, out, err = run(["uv", "run", "aegis", "init"], cwd=root)
print(f"1. init rc={rc}")

# 2. Check with violations
rc, out, err = run(["uv", "run", "aegis", "check", "--exit-code"], cwd=root)
print(f"2. check rc={rc}")
print(f"   violations: {len([l for l in out.splitlines() if l.strip().startswith('-')])}")

# 3. Check --json
rc, out, err = run(["uv", "run", "aegis", "check", "--json"], cwd=root)
print(f"3. check --json rc={rc}")
try:
    d = json.loads(out)
    print(f"   parsed ok: passed={d.get('passed')}, violations={len(d.get('violations', []))}")
except Exception as e:
    print(f"   parse failed: {e}")
    print(f"   out[:300]: {out[:300]}")

# 4. Baseline
rc, out, err = run(["uv", "run", "aegis", "baseline"], cwd=root)
print(f"4. baseline rc={rc}")
bp = os.path.join(root, ".aegis", "baseline.json")
if os.path.exists(bp):
    with open(bp) as f:
        bl = json.load(f)
    print(f"   baseline entries: {len(bl)}")
else:
    print("   NO BASELINE FILE")

# 5. Check after baseline
rc, out, err = run(["uv", "run", "aegis", "check", "--exit-code"], cwd=root)
print(f"5. check after baseline rc={rc}")
print(f"   output: {out[:300]}")

# 6. Rules install testing
rc, out, err = run(["uv", "run", "aegis", "rules", "install", "testing"], cwd=root)
print(f"6. rules install testing rc={rc}")
print(f"   out: {out[:200]}")
print(f"   err: {err[:200]}")

# 7. Rules reset
rc, out, err = run(["uv", "run", "aegis", "rules", "reset"], cwd=root)
print(f"7. rules reset rc={rc}")
print(f"   out: {out[:200]}")
print(f"   err: {err[:200]}")

shutil.rmtree(root, ignore_errors=True)
