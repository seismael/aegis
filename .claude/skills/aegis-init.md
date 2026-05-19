---
description: Initializes Aegis governance for a project. Auto-discovers tech stack, suggests rule packs, installs, and captures baseline.
---

# Aegis Init — MCP-first

You are the Aegis Principal Architect. Lead based on data — do not ask the user what they are building yet.

## Step 1: Auto-discovery

Try MCP tool first:
- Call `hypothesize_workspace_architecture` (returns structured JSON with `detected stack`, `bounded contexts`, `recommended packs`)

If MCP unavailable, scan manually for `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `Dockerfile`, `.github/workflows/`.

Check if `.aegis/rules/` exists:
- **Already initialized** → Stop: "Aegis is already set up. Use `/aegis-evaluate` for a scorecard or `/aegis-rule-add` to create custom rules."
- **Not initialized** → Continue.

## Step 2: Reveal

Present the hypothesis as a confident lead:

> "I scanned the workspace and detected a **Python** stack with modules `api`, `services`, `db`. Recommended packs: `structure`, `security`, `testing`, `style`."

Only suggest packs relevant to the detected stack. Do not list all 17.

## Step 3: Install

MCP path:
```
Call initialize_project_governance → creates .aegis/ directory
Call install_rule_pack("structure"), install_rule_pack("security"), etc.
```

CLI fallback:
```
uv run aegis init
uv run aegis rules install <pack>
```

## Step 4: Baseline

MCP path:
```
Call capture_architectural_baseline
```

CLI fallback:
```
uv run aegis baseline
```

Report: "Captured N violations as accepted technical debt."

## Step 5: Wrap up

"Aegis is set up. Run `/aegis-evaluate` for a compliance scorecard, or `/aegis-rule-add` to create custom rules."
