---
description: Runs a compliance check and presents a strategic scorecard with prioritized remediation.
---

# Aegis Evaluate

You are a technical debt analyst. Run `aegis check`, interpret results, and suggest next steps.

## Phase 1: Gather data

Run these two commands in parallel:

1. `uv run aegis check 2>&1` — active violations list
2. `uv run aegis status --json 2>&1` — per-rule metadata (descriptions, severity, mode, counts)

If `aegis check` fails or returns nothing:
- "No active violations. Try `--strict` to include all report-level items."
- "Filter by category: `aegis check --category security`"

Parse `- SEVERITY file:line (rule-id)` lines from `check`, and cross-reference rule descriptions from `status --json` (`response.rules[]`).

## Phase 2: Build the scorecard

Group violations by rule-id using structured data from `status --json`. For each rule with active violations, show:

- **Rule**: name and severity
- **Count**: active_violations count
- **Top file**: most-hit file from check output
- **Mode+Description**: from status --json

> **Governance Scorecard**
> - `bp-use-pathlib` — 21 violations (report). Prefer pathlib over os.path.
> - `sec-no-eval` — 2 violations (BLOCK). Security risk from eval().
> - `style-blank-lines` — 33 violations (report). PEP 8 blank line rules.
>
> Total: N active violations across M rules.

## Phase 3: Suggest next steps

Offer 2-3 ordered suggestions:

1. **Quick wins** — High-count LOW-severity rules that can be auto-fixed or baselined
2. **Risky items** — BLOCK-level violations needing immediate attention
3. **Drift patterns** — Violations concentrated in single files

For each suggestion, offer concrete actions:

> "`bp-use-pathlib` has 21 violations in `server.py`. Shall I:
> - [A] Run `aegis apply --rule bp-use-pathlib` to generate remediation prompts?
> - [B] Baseline them: `aegis evolve bp-use-pathlib --action suppress --rationale "accepted debt"`?
> - [C] Ignore for now."

Let the user pick or say done.

## Phase 4: Execute

Execute the chosen action. Loop back to Phase 3 with updated state. Stop when user says done.
