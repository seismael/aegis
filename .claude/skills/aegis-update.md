---
description: Reviews governance posture for improvement opportunities — zombie rules, escalation candidates, and pack gaps.
---

# Aegis Update

You are a governance optimization advisor. Analyze the rule set for stale or underperforming rules.

## Step 1: Gather data

Run `uv run aegis status --json` and capture `response.rules[]`. Each entry has: `id`, `description`, `severity`, `mode`, `active_violations`, `baseline_entries`.

Also run `uv run aegis rules phases` for phase distribution.

## Step 2: Find improvement opportunities

Analyze the `status --json` rule array for three patterns:

**Zombie rules** — `active_violations == 0 AND baseline_entries == 0` (rules matching nothing, ever)
> "`bp-walrus-appropriate` has never matched anything. Consider removing or downgrading to report."

**Escalation candidates** — `mode in (report, warn) AND active_violations == 0 AND baseline_entries > 0` (rules everyone complies with)
> "`bp-explicit-exceptions` has 0 active violations. Consider upgrading from report to warn."

**Pack gaps** — Based on tech stack (Dockerfiles → `infrastructure` pack, etc.)
> "Dockerfiles exist but `infrastructure` pack is not installed."

## Step 3: Present

> "Found N opportunities:
> - N zombie rules (remove/downgrade)
> - N escalation candidates (tighten)
> - N missing packs
>
> Which area should I walk through?"

Let user pick an area. Present one suggestion, ask for decision, act, loop.

## Step 4: Apply

| Change | Command |
|--------|---------|
| Mode/severity | Edit `.aegis/rules/<category>/rules.yaml` |
| Install pack | `uv run aegis rules install <pack>` |
| Remove pack | `uv run aegis rules remove <pack>` |

After each change, verify: `uv run aegis check --rule <id>`.

## Step 5: Summarize

> "Applied 3 optimizations: removed 1 zombie, escalated 1 to warn, installed `infrastructure`. Run `/aegis-evaluate` for scorecard."
