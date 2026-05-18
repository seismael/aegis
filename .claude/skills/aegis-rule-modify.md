---
description: Modifies an existing rule — severity, scope, mode, or phase. The AI evaluates impact before applying.
---

# Aegis Rule Modify

You are a governance evolution specialist. Help the user modify a rule without breaking compliance posture.

## Step 1: Pick the rule

Run `uv run aegis status --json` and show available rules (id + description + severity + mode + active_violations).

> "Which rule? Tell me the ID or describe what you want to change."

If the user describes behavior, search by keyword across descriptions.

## Step 2: Show current state

Run `uv run aegis check --rule <id>` and `uv run aegis status --json` (parse the single rule entry). Present:

> **`bp-no-mutable-defaults`** (MEDIUM, warn) — 0 active violations
> Mutable default arguments cause shared-state bugs.

"Change: severity, mode, scope, or phase?"

## Step 3: Preview impact

| Change | Effect |
|--------|--------|
| MEDIUM→HIGH | Promotes 3 violations from warn→block. Needs baseline. |
| Narrow scope to exclude tests/ | Reduces violations from 12→3. |
| report→block | All active violations become blocking. |

"Apply this change? Baseline newly-blocked violations?"

## Step 4: Apply

1. Edit `.aegis/rules/<category>/rules.yaml`
2. `uv run aegis check --rule <id>` — verify still works
3. If baselining: `uv run aegis evolve <id> --action suppress --rationale "<reason>"`
4. For permanent record: `uv run aegis evolve <id> --action relax_rule --rationale "<reason>"`

## Step 5: Confirm

> "Updated `<id>`: MEDIUM→HIGH, warn→block, excluded tests/. Run `/aegis-evaluate` to verify."
