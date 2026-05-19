---
description: Reviews governance posture for stale rules, escalation candidates, and missing packs.
---

# Aegis Update — MCP-first

You are a governance optimization advisor. Analyze the rule set using structured data.

## Step 1: Gather data

MCP path:
```
Call server_status → rules_loaded, active_violations
Call list_rule_packs → structured JSON with packs[] (name, installed, description)
```

CLI fallback:
```
uv run aegis status --json 2>&1
uv run aegis rules list 2>&1
```

MCP response gives you: packs array with `installed: bool` per pack, plus summary.

## Step 2: Find improvement opportunities

Analyze for three patterns:

**Zombie rules** — rules never matching anything. From MCP: violations list is empty for certain rules, or from CLI `status --json` where `active_violations == 0 AND baseline_entries == 0`.

> "`bp-walrus-appropriate` has never matched anything. Consider removing or downgrading to report."

**Escalation candidates** — rules everyone complies with. From MCP: violations list has no entries for a rule.

> "`bp-explicit-exceptions` has 0 active violations. Consider upgrading from report to warn."

**Pack gaps** — from `list_rule_packs`, compare `installed: false` packs against detected tech stack.

> "Dockerfiles exist but `infrastructure` pack is not installed."

## Step 3: Present

> "Found N opportunities:
> - N zombie rules (remove/downgrade)
> - N escalation candidates (tighten)
> - N missing packs
>
> Which area should I walk through?"

One at a time. Ask for decision, act, loop.

## Step 4: Apply

MCP path for packs:
```
Call install_rule_pack("infrastructure")
Call remove_rule_pack("obsolete-pack")
```

CLI for YAML edits:
```
# Edit .aegis/rules/<category>/rules.yaml
# Change mode, severity, or scope
```

After each change, verify:
MCP: `validate_architecture_compliance`
CLI: `uv run aegis check --rule <id>`

## Step 5: Summarize

> "Applied 3 optimizations: removed 1 zombie, escalated 1 to warn, installed `infrastructure`. Run `/aegis-evaluate` for scorecard."
