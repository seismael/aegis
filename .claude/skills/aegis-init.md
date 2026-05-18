---
description: Initializes Aegis governance for a project. Guides the user through tech-stack detection, rule-pack selection, and initial baseline.
---

# Aegis Init

Guide the user through a lightweight setup. One question at a time, use `aegis` CLI to drive real changes.

## Step 1: Check existing state

Run `uv run aegis status --json 2>nul` and check if `.aegis/rules/` exists.

- **Already initialized** → "Aegis is already set up. Use `/aegis-evaluate` or `/aegis-rule-add` to refine governance."
- **Not initialized** → Run `uv run aegis init`. Then proceed.

## Step 2: Tech-stack suggestion

Scan the repo for `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `Dockerfile`, `.github/workflows/`. Present a compact summary and recommend 2-4 packs:

> "I see a **Python** project with **Docker** and **GitHub Actions**. Recommended packs:"
> - `python-best-practices` — Python idioms
> - `security` — zero-tolerance security rules
> - `testing` — test conventions
> - `dependencies` — supply-chain hygiene

Ask: "Shall I install these, pick different ones, or skip?"

If user agrees, run `uv run aegis rules install <pack>` for each. To customize, list all packs via `uv run aegis rules list`.

## Step 3: Baseline

After packs installed:

> "I'll scan the workspace and baseline existing violations so only NEW violations are flagged."

Run `uv run aegis baseline`. Show the result:
> "Captured N violations as accepted technical debt. N rules active across M packs."

## Step 4: Wrap up

> "Aegis is set up. Run `/aegis-evaluate` for a compliance scorecard, or `/aegis-rule-add` to create custom rules."
