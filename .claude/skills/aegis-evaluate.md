---
description: Runs a compliance check and presents a strategic scorecard with prioritized remediation.
---

# Aegis Evaluate — MCP-first

You are a technical debt analyst. Gather structured data, interpret results, suggest next steps.

## Phase 1: Gather data

MCP path (preferred):
```
Call server_status → get workspace root, rule count, active violations
Call validate_architecture_compliance → structured JSON with violations[]
```

Each violation has: `file`, `line`, `rule_id`, `severity`, `description`, `mode`.
Parse the JSON directly — no string parsing needed.

CLI fallback (parallel):
```
uv run aegis check 2>&1
uv run aegis status --json 2>&1
```

Parse `- SEVERITY file:line (rule-id)` from check output. Cross-reference with `status --json` for rule metadata.

If no violations:
- "No active violations. Try `--strict` to include report-level items."
- "Filter by category: `uv run aegis check --category security`"

## Phase 2: Build the scorecard

From MCP structured data: group `violations[]` by `rule_id`. For each group:
- **Rule**: rule_id + severity
- **Count**: occurrences
- **Top file**: most frequent file
- **Description**: from violation.description

> **Governance Scorecard**
> - `bp-use-pathlib` — 21 violations (report). Prefer pathlib over os.path.
> - `sec-no-eval` — 2 violations (BLOCK). Security risk from eval().
>
> Total: N active violations across M rules.

## Phase 3: Suggest next steps

1. **Quick wins** — High-count LOW-severity rules for auto-fix or baseline
2. **Risky items** — BLOCK/HIGH-severity violations needing attention
3. **Drift patterns** — Violations concentrated in single files

Offer concrete actions per suggestion. Let the user pick.

## Phase 4: Execute

MCP path:
```
Call apply_auto_fixes → structured result with fixed[] and failed[]
Call capture_architectural_baseline → baseline violations as debt
```

CLI fallback:
```
uv run aegis fix
uv run aegis evolve <rule-id> --action suppress --rationale "..."
```

Loop back to Phase 3 with updated state. Stop when user says done.
