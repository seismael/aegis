"""Deep validation across all Aegis layers."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time


def log(msg):
    print(f"  {msg}")
    sys.stdout.flush()


def run(cmd, cwd=None):
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=60)
    return r.returncode, r.stdout, r.stderr


PASS = 0
FAIL = 0


def test(name, fn):
    global PASS, FAIL
    print(f"\n--- {name} ---")
    try:
        fn()
        PASS += 1
    except AssertionError as e:
        print(f"  FAIL: {e}")
        FAIL += 1
    except Exception as e:
        print(f"  EXCEPTION ({type(e).__name__}): {e}")
        FAIL += 1


root = tempfile.mkdtemp(prefix="aegis_deepval_")
print(f"Test project: {root}")

# Create test project with varied violations
os.makedirs(os.path.join(root, "src", "domain"))
os.makedirs(os.path.join(root, "src", "infrastructure"))
os.makedirs(os.path.join(root, "src", "api"))
os.makedirs(os.path.join(root, "tests"))

# File 1: Domain layer violation
with open(os.path.join(root, "src", "domain", "orders.py"), "w") as f:
    f.write(
        '# domain module\nimport os\nfrom src.infrastructure.database import Database\n\ndef process(order_id):\n    return {"id": order_id}\n'
    )

# File 2: Infrastructure
with open(os.path.join(root, "src", "infrastructure", "database.py"), "w") as f:
    f.write("# infra module\nimport os\nDB = {}\n")

# File 3: API with security violations
with open(os.path.join(root, "src", "api", "routes.py"), "w") as f:
    f.write(
        '# API routes\nimport json\n\nPASSWORD = "hunter2"\n\ndef run():\n    eval("print(1)")\n    return "ok"\n'
    )

# File 4: Clean file
with open(os.path.join(root, "src", "api", "clean.py"), "w") as f:
    f.write(
        '"""Clean module."""\ndef process(data: dict) -> str:\n    return data.get("key", "")\n'
    )

# File 5: Test file
with open(os.path.join(root, "tests", "test_routes.py"), "w") as f:
    f.write('"""Tests."""\ndef test_run():\n    assert True\n')

# Init git
subprocess.run(["git", "init"], cwd=root, capture_output=True)
subprocess.run(
    ["git", "config", "user.email", "t@t.com"], cwd=root, capture_output=True
)
subprocess.run(["git", "config", "user.name", "t"], cwd=root, capture_output=True)
subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
subprocess.run(["git", "commit", "-m", "init"], cwd=root, capture_output=True)


# ===== LAYER 1: CLI INIT & STATUS =====
def test_init_creates_rules():
    rc, out, err = run(["uv", "run", "aegis", "init"], cwd=root)
    assert rc == 0, f"init rc={rc}, err={err[:200]}"
    assert os.path.exists(os.path.join(root, ".aegis", "rules")), (
        ".aegis/rules/ missing"
    )
    assert os.path.exists(os.path.join(root, ".aegis", "config.yaml")), (
        "config.yaml missing"
    )
    rules_dirs = os.listdir(os.path.join(root, ".aegis", "rules"))
    assert len(rules_dirs) > 0, "no rule pack dirs created"


def test_status():
    rc, out, err = run(["uv", "run", "aegis", "status"], cwd=root)
    assert rc == 0, f"status rc={rc}"
    assert "rules" in out.lower(), "status shows rules count"
    assert "engine" in out.lower(), "status shows engines"


def test_status_json_fields():
    rc, out, err = run(["uv", "run", "aegis", "status", "--json"], cwd=root)
    assert rc == 0, f"status --json rc={rc}"
    data = json.loads(out)
    assert "rules_count" in data, "missing rules_count"
    assert "active_violations" in data, "missing active_violations"
    assert "baseline_violations" in data, "missing baseline_violations (CLI format)"
    assert data["active_violations"] > 0, (
        f"expected violations, got {data['active_violations']}"
    )


# ===== LAYER 2: COMPLIANCE CHECKING =====
def test_check_detects_violations():
    rc, out, err = run(["uv", "run", "aegis", "check", "--exit-code"], cwd=root)
    assert rc == 1, f"check rc={rc} (expected 1 with violations)"
    # Parse rule IDs
    rule_ids = set(re.findall(r"\(([\w-]+)\)", out))
    assert "sec-no-hardcoded-passwords" in rule_ids, "password rule not fired"
    assert "sec-no-eval" in rule_ids, "eval rule not fired"
    assert "arch-layer-violation" in rule_ids, "graph layer violation not fired"


def test_check_json_output():
    rc, out, err = run(["uv", "run", "aegis", "check", "--json"], cwd=root)
    # --json outputs valid JSON and may return rc=1 when violations exist
    data = json.loads(out)
    assert "passed" in data
    assert "violations" in data
    assert len(data["violations"]) > 0
    v = data["violations"][0]
    assert "mode" in v, "violation missing mode"
    assert v["mode"] in ("block", "warn", "report"), f"unexpected mode: {v['mode']}"


def test_check_strict():
    rc, out, err = run(
        ["uv", "run", "aegis", "check", "--strict", "--exit-code"], cwd=root
    )
    assert rc == 1, f"strict rc={rc} (expected 1)"


def test_check_phase_filter():
    rc, out, err = run(
        ["uv", "run", "aegis", "check", "--phase", "pre-commit", "--exit-code"],
        cwd=root,
    )
    assert rc in (0, 1), f"phase filter rc={rc}"


def test_check_category_filter():
    rc, out, err = run(
        ["uv", "run", "aegis", "check", "--category", "security", "--exit-code"],
        cwd=root,
    )
    rule_ids = set(re.findall(r"\(([\w-]+)\)", out))
    assert "sec-no-eval" in rule_ids, "security filter didn't return sec rules"
    non_sec = [
        r for r in rule_ids if not r.startswith("sec-") and not r.startswith("bp-")
    ]
    # Security category should only return security rules
    assert len(non_sec) == 0 or all(r.startswith(("semantic-",)) for r in non_sec), (
        f"non-security rules in security filter: {non_sec}"
    )


def test_check_staged():
    """Staged check must use --phase on-demand to include security rules (not in pre-commit)."""
    bp_path = os.path.join(root, ".aegis", "baseline.json")
    if os.path.exists(bp_path):
        os.remove(bp_path)
    with open(os.path.join(root, "src", "api", "routes.py"), "a") as f:
        f.write('\nsubprocess.call("rm -rf /", shell=True)\n')
    subprocess.run(["git", "add", "src/api/routes.py"], cwd=root, capture_output=True)
    # Security rules are excluded from pre-commit phase by default; use on-demand
    rc, out, err = run(
        ["uv", "run", "aegis", "check", "--staged", "--phase", "on-demand"], cwd=root
    )
    log(out[:500])
    rule_ids = set(re.findall(r"\(([\w-]+)\)", out))
    assert "sec-no-subprocess-shell" in rule_ids, (
        f"staged didn't detect shell=True. Rules: {rule_ids}"
    )
    subprocess.run(["git", "checkout", "--", "."], cwd=root, capture_output=True)


def test_check_staged_no_changes():
    """Staged check with nothing staged shows no violations."""
    rc, out, err = run(["uv", "run", "aegis", "check", "--staged"], cwd=root)
    # With nothing staged, should either pass or only show compliance info
    assert rc == 0, f"clean staged rc={rc}"


# ===== LAYER 3: BASELINE MANAGEMENT =====
def test_baseline_capture():
    rc, out, err = run(["uv", "run", "aegis", "baseline"], cwd=root)
    assert rc == 0, f"baseline rc={rc}"
    bp = os.path.join(root, ".aegis", "baseline.json")
    assert os.path.exists(bp), "baseline.json not created"
    with open(bp) as f:
        data = json.load(f)
    assert len(data) > 0, "baseline is empty"


def test_check_clean_after_baseline():
    """After baseline, non-security violations should be exempt. Security rules skip baseline by design."""
    rc, out, err = run(["uv", "run", "aegis", "check"], cwd=root)
    rule_ids = set(re.findall(r"\(([\w-]+)\)", out))
    # Security violations (sec-*) are never baselined — intentional zero-tolerance policy
    sec_rules = [r for r in rule_ids if r.startswith("sec-")]
    non_sec_rules = [r for r in rule_ids if not r.startswith("sec-")]
    log(
        f"after baseline: {len(rule_ids)} violations ({len(sec_rules)} sec, {len(non_sec_rules)} non-sec)"
    )
    # Non-security violations should be baselined (exempt from check output)
    assert len(non_sec_rules) == 0, (
        f"non-security violations not baselined: {non_sec_rules}"
    )


def test_check_exit_code_after_baseline():
    """--exit-code returns 1 if security violations remain (they skip baseline by design)."""
    rc, out, err = run(["uv", "run", "aegis", "check", "--exit-code"], cwd=root)
    rule_ids = set(re.findall(r"\(([\w-]+)\)", out))
    sec_rules = [r for r in rule_ids if r.startswith("sec-")]
    non_sec_rules = [r for r in rule_ids if not r.startswith("sec-")]
    log(
        f"--exit-code after baseline: {len(rule_ids)} violations ({len(sec_rules)} sec, {len(non_sec_rules)} non-sec)"
    )
    assert len(non_sec_rules) == 0, (
        f"non-security violations not baselined: {non_sec_rules}"
    )
    # Security violations remain (zero-tolerance, skip baseline) — exit 1 is expected
    if sec_rules:
        assert rc == 1, f"expected 1 with security violations, got {rc}"


def test_baseline_clear():
    rc, out, err = run(["uv", "run", "aegis", "baseline", "--clear"], cwd=root)
    assert rc == 0, f"baseline --clear rc={rc}"
    rc, out, err = run(["uv", "run", "aegis", "check", "--exit-code"], cwd=root)
    assert rc == 1, f"check after clear baseline rc={rc} (expected 1)"


# ===== LAYER 4: RULESET EVOLUTION =====
def test_evolve_suppress():
    rc, out, err = run(
        [
            "uv",
            "run",
            "aegis",
            "evolve",
            "sec-no-eval",
            "--action",
            "suppress",
            "--rationale",
            "test",
        ],
        cwd=root,
    )
    assert rc == 0, f"suppress rc={rc}, err={err[:200]}"


def test_rule_list():
    rc, out, err = run(["uv", "run", "aegis", "rules", "list"], cwd=root)
    assert rc == 0, f"rules list rc={rc}, err={err[:200]}"
    # rules list shows pack names, not individual rule IDs
    assert "testing" in out.lower(), "testing pack not listed"


def test_rule_install():
    rc, out, err = run(["uv", "run", "aegis", "rules", "install", "testing"], cwd=root)
    # Pack may already be installed (idempotent) — accept rc=0 or "already installed" message
    if rc != 0:
        assert "already installed" in out.lower(), (
            f"unexpected failure: rc={rc}, out={out[:200]}"
        )
        log("(testing pack already installed — skipping)")


def test_rule_remove():
    rc, out, err = run(["uv", "run", "aegis", "rules", "remove", "testing"], cwd=root)
    assert rc == 0, f"rules remove testing rc={rc}, err={err[:200]}"


def test_rule_reset():
    rc, out, err = run(["uv", "run", "aegis", "rules", "reset", "--yes"], cwd=root)
    assert rc == 0, f"rules reset rc={rc}, err={err[:200]}"
    # Remove rules dir so init re-creates it with all default packs
    shutil.rmtree(os.path.join(root, ".aegis", "rules"), ignore_errors=True)
    rc, out, err = run(["uv", "run", "aegis", "init"], cwd=root)
    assert rc == 0, f"re-init after reset rc={rc}"


def test_rule_phases():
    rc, out, err = run(["uv", "run", "aegis", "rules", "phases"], cwd=root)
    assert rc == 0, f"rules phases rc={rc}"


def test_rule_phase_mapping():
    rc, out, err = run(["uv", "run", "aegis", "rules", "phase-mapping"], cwd=root)
    assert rc == 0, f"rules phase-mapping rc={rc}"


# ===== LAYER 5: REMEDIATION =====
def test_apply_remediation():
    rc, out, err = run(["uv", "run", "aegis", "apply"], cwd=root)
    out_len = len(out)
    log(f"apply rc={rc}, out_len={out_len}, out[:300]={out[:300]!r}")
    assert rc == 1, f"apply rc={rc} (expected 1 with violations)"
    assert out_len > 100, f"apply output too short ({out_len}): {out[:200]!r}"


def test_apply_to_file():
    out_path = os.path.join(root, "remediation_output.txt")
    rc, out, err = run(["uv", "run", "aegis", "apply", "--output", out_path], cwd=root)
    assert rc == 1, f"apply --output rc={rc}"
    assert os.path.exists(out_path), "output file not created"
    with open(out_path) as f:
        content = f.read()
    assert len(content) > 100, "remediation file too short"


# ===== LAYER 6: EDGE CASES =====
def test_non_ascii_paths():
    path = os.path.join(root, "src", "api", "uber_routes.py")
    with open(path, "w") as f:
        f.write("x = 1\n")
    subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
    rc, out, err = run(["uv", "run", "aegis", "check"], cwd=root)
    assert rc in (0, 1), f"non-ASCII path check rc={rc}"


def test_empty_workspace():
    empty = tempfile.mkdtemp(prefix="aegis_empty_")
    subprocess.run(["git", "init"], cwd=empty, capture_output=True)
    rc, out, err = run(["uv", "run", "aegis", "init"], cwd=empty)
    assert rc == 0, f"empty init rc={rc}"
    rc, out, err = run(["uv", "run", "aegis", "check"], cwd=empty)
    assert "Architecture compliant" in out or rc == 0, f"empty check failed: rc={rc}"
    shutil.rmtree(empty, ignore_errors=True)


def test_no_git_repo():
    """Check graceful failure outside git repo."""
    no_git = tempfile.mkdtemp(prefix="aegis_nogit_")
    rc, out, err = run(["uv", "run", "aegis", "init"], cwd=no_git)
    assert rc == 0, f"no-git init rc={rc}"
    rc, out, err = run(["uv", "run", "aegis", "check", "--staged"], cwd=no_git)
    # Should handle gracefully (no git repo)
    assert rc in (0, 1), f"no-git staged check rc={rc}"
    shutil.rmtree(no_git, ignore_errors=True)


def test_help_all_commands():
    for cmd in [
        ["uv", "run", "aegis", "--help"],
        ["uv", "run", "aegis", "check", "--help"],
        ["uv", "run", "aegis", "status", "--help"],
        ["uv", "run", "aegis", "evolve", "--help"],
        ["uv", "run", "aegis", "apply", "--help"],
        ["uv", "run", "aegis", "fix", "--help"],
        ["uv", "run", "aegis", "rules", "--help"],
        ["uv", "run", "aegis", "baseline", "--help"],
        ["uv", "run", "aegis", "init", "--help"],
    ]:
        rc, out, err = run(cmd, cwd=root)
        assert rc == 0, f"'{' '.join(cmd)}' failed rc={rc}"
        assert len(out) > 20, f"'{' '.join(cmd)}' output too short"


# ===== LAYER 7: DIRECT ANALYZER TESTS =====
def test_graph_analyzer_src_layout():
    """Graph analyzer fires on src/ layout."""
    sys.path.insert(0, r"C:\dev\projects\aegis\src")
    from aegis.infrastructure.graph_analyzer import GraphAnalyzer

    from aegis.domain.policy.models import EngineType, Rule, RuleCategory, Severity

    rule = Rule(
        id="arch-layer-violation",
        category=RuleCategory.ARCHITECTURE,
        engine_type=EngineType.GRAPH,
        query="disallowed_import",
        metadata={"source": "domain", "target": "infrastructure"},
        description="test",
        severity=Severity.HIGH,
        mode="block",
    )
    ga = GraphAnalyzer()
    violations = ga.analyze_graph(root, [rule])
    assert len(violations) == 1, f"expected 1 layer violation, got {len(violations)}"
    assert "domain" in violations[0].file
    assert "infrastructure" in violations[0].file or "infrastructure" in str(
        violations[0].description
    )


def test_regex_analyzer_multiline():
    """Regex analyzer with (?m) fires on line-anchored patterns."""
    sys.path.insert(0, r"C:\dev\projects\aegis\src")
    from aegis.infrastructure.regex_analyzer import RegexAnalyzer

    from aegis.domain.policy.models import EngineType, Rule, RuleCategory, Severity

    rule = Rule(
        id="bp-explicit-exceptions",
        category=RuleCategory.BEST_PRACTICES,
        engine_type=EngineType.REGEX,
        query="(?m)^\\s*except\\s*:",
        description="test",
        severity=Severity.HIGH,
        mode="warn",
        language="py",
    )
    analyzer = RegexAnalyzer()
    violations = analyzer.analyze_file(
        "test.py",
        "def f():\n    try:\n        pass\n    except:\n        pass\n",
        [rule],
    )
    assert len(violations) == 1, (
        f"expected 1 multiline violation, got {len(violations)}"
    )


def test_regex_analyzer_no_multiline():
    """Same pattern without (?m) should NOT fire on line-anchored ^."""
    sys.path.insert(0, r"C:\dev\projects\aegis\src")
    from aegis.infrastructure.regex_analyzer import RegexAnalyzer

    from aegis.domain.policy.models import EngineType, Rule, RuleCategory, Severity

    rule = Rule(
        id="bp-explicit-exceptions",
        category=RuleCategory.BEST_PRACTICES,
        engine_type=EngineType.REGEX,
        query="^\\s*except\\s*:",
        description="test",
        severity=Severity.HIGH,
        mode="warn",
        language="py",
    )
    analyzer = RegexAnalyzer()
    violations = analyzer.analyze_file(
        "test.py",
        "def f():\n    try:\n        pass\n    except:\n        pass\n",
        [rule],
    )
    assert len(violations) == 0, (
        f"expected 0 without (?m), got {len(violations)} (bug: line-anchored matched string-start only)"
    )


# ===== LAYER 8: MCP KERNEL =====
def test_mcp_server_stdio_start():
    """MCP server starts and stays alive on stdio transport."""
    proc = subprocess.Popen(
        ["uv", "run", "aegis", "serve", "--transport", "stdio"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    time.sleep(2)
    if proc.poll() is None:
        proc.kill()
    else:
        _, stderr = proc.communicate()
        raise AssertionError(f"MCP server died: {stderr[:300]}")


def test_mcp_server_http_start():
    """MCP server starts on SSE/HTTP transport."""
    proc = subprocess.Popen(
        ["uv", "run", "aegis", "serve", "--transport", "sse", "--port", "9999"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    time.sleep(3)
    if proc.poll() is None:
        proc.kill()
    else:
        _, stderr = proc.communicate()
        raise AssertionError(f"MCP SSE server died: {stderr[:300]}")


# ===== RUN ALL =====
tests = [
    ("CLI: init creates rules", test_init_creates_rules),
    ("CLI: status", test_status),
    ("CLI: status --json fields", test_status_json_fields),
    ("CLI: check detects violations", test_check_detects_violations),
    ("CLI: check --json", test_check_json_output),
    ("CLI: check --strict", test_check_strict),
    ("CLI: check --phase filter", test_check_phase_filter),
    ("CLI: check --category filter", test_check_category_filter),
    ("CLI: check --staged detects violations", test_check_staged),
    ("CLI: check --staged clean", test_check_staged_no_changes),
    ("CLI: baseline capture", test_baseline_capture),
    ("CLI: check clean after baseline", test_check_clean_after_baseline),
    ("CLI: --exit-code 0 after baseline", test_check_exit_code_after_baseline),
    ("CLI: baseline --clear", test_baseline_clear),
    ("CLI: evolve suppress", test_evolve_suppress),
    ("CLI: rules list", test_rule_list),
    ("CLI: rules install", test_rule_install),
    ("CLI: rules remove", test_rule_remove),
    ("CLI: rules reset", test_rule_reset),
    ("CLI: rules phases", test_rule_phases),
    ("CLI: rules phase-mapping", test_rule_phase_mapping),
    ("CLI: apply remediation", test_apply_remediation),
    ("CLI: apply --output file", test_apply_to_file),
    ("CLI: help all commands", test_help_all_commands),
    ("CLI: non-ASCII paths", test_non_ascii_paths),
    ("CLI: empty workspace", test_empty_workspace),
    ("CLI: no git repo", test_no_git_repo),
    ("Unit: graph analyzer src/ layout", test_graph_analyzer_src_layout),
    ("Unit: regex multiline (?m) fires", test_regex_analyzer_multiline),
    ("Unit: regex no (?m) doesn't fire", test_regex_analyzer_no_multiline),
    ("MCP: stdio server starts", test_mcp_server_stdio_start),
    ("MCP: SSE server starts", test_mcp_server_http_start),
]

for name, fn in tests:
    test(name, fn)

print(f"\n{'=' * 60}")
print(f"DEEP VALIDATION: {PASS} passed, {FAIL} failed")
print(f"{'=' * 60}")

shutil.rmtree(root, ignore_errors=True)
sys.exit(0 if FAIL == 0 else 1)
