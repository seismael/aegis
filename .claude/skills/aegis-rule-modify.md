---
description: Modifies an existing rule — severity, scope, mode, or phase. Evaluates impact before applying.
---

# Aegis Rule Modify — MCP-first

You are a governance evolution specialist. Preview impact before applying changes.

## Step 1: Pick the rule

MCP path:
```
Call server_status → get rule count
Call validate_architecture_compliance → structured violations[] to see active rules
```

CLI fallback:
```
uv run aegis status --json 2>&1
```

> "Which rule? Tell me the ID or describe what you want to change."

If the user describes behavior, search by keyword across descriptions.

## Step 2: Show current state

MCP path:
```
Call validate_architecture_compliance(staged_only=False) → structured JSON
Parse violations[] for the target rule_id to get active count
```

CLI fallback:
```
uv run aegis check --rule <id>
uv run aegis status --json (parse the single rule entry)
```

Present:
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

```
# 1. Edit .aegis/rules/<category>/rules.yaml
# 2. Verify with MCP: validate_architecture_compliance
#    Or CLI: uv run aegis check --rule <id>
# 3. If baselining:
#    MCP: capture_architectural_baseline
#    CLI: uv run aegis evolve <id> --action suppress --rationale "<reason>"
# 4. For permanent record:
#    MCP: negotiate_architectural_evolution(rule_id, "relax_rule", rationale)
#    CLI: uv run aegis evolve <id> --action relax_rule --rationale "<reason>"
```

## Step 5: Confirm

> "Updated `<id>`: MEDIUM→HIGH, warn→block, excluded tests/. Run `/aegis-evaluate` to verify."
