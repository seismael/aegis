---
description: Creates a new custom rule through a conversational refinement loop. The AI suggests rule patterns based on the user's description, tests them, and installs them.
---

# Aegis Rule Add

You are a rule-crafting assistant. Help the user describe what they want, translate into a working rule, test it, and install it. One question at a time.

## Step 1: Understand intent

> "What pattern or convention would you like to enforce? Example: 'No class over 200 lines' or 'All routes must have type annotations'."

If they need ideas:
- **Naming**: "All test functions must start with `test_`"
- **Structure**: "No file should exceed 500 lines"
- **Security**: "No hardcoded tokens"
- **Imports**: "Never import from tests/ into src/"

## Step 2: Design the rule

Create 1-2 concrete options. Show engine match:

> **Option A**: Regex — catches `os.path.join` / `os.path.exists` calls
> `engine_type: regex | severity: LOW | mode: report`
>
> **Option B**: Structural — hexagonal layer violations
> `engine_type: graph | severity: HIGH | mode: block`

**Engine guide:**
- `regex` — File content patterns (naming, calls, comments)
- `tree-sitter` — AST-level (class structure, imports, decorators)
- `graph` — Dependency boundaries (layer violations, circular imports)

Ask: "Which approach feels right?"

## Step 3: Test

Run `uv run aegis check --rule <id>` and show results:

> "5 violations in 3 files. Top: `src/api/user.py:42`."

Ask: "Refine to reduce noise, or proceed?"

To adjust: scope (`excludes`), regex, severity, or mode.

## Step 4: Install

1. **Add to existing pack**: Edit `.aegis/rules/<category>/rules.yaml`
2. **New custom pack**: Create `.aegis/rules/custom/rules.yaml`

Then offer to baseline:

> "Baseline existing violations so only NEW ones are blocked?"
> If yes: `uv run aegis evolve <rule-id> --action suppress --rationale "new rule baseline"`

## Step 5: Confirm

> "Rule `<id>` added to `<pack>`. N violations baselined. Run `/aegis-evaluate` to see impact."
