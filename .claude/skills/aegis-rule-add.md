---
description: Creates a new custom rule through a conversational refinement loop. Tests and installs it.
---

# Aegis Rule Add — MCP-first

You are a rule-crafting assistant. One question at a time. Test before installing.

## Step 1: Understand intent

> "What pattern or convention would you like to enforce? Example: 'No class over 200 lines' or 'All routes must have type annotations'."

If they need ideas:
- **Naming**: "All test functions must start with `test_`"
- **Structure**: "No file should exceed 500 lines"
- **Security**: "No hardcoded tokens"
- **Imports**: "Never import from tests/ into src/"

## Step 2: Design the rule

Create 1-2 options. Show engine match:

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

## Step 3: Test via MCP

MCP path:
```
Call get_relevant_rules("src/test/file.py") → confirms scoping works
Call evaluate_code_delta(code_string=test_code, language="py") → structured JSON with violations
```

CLI fallback:
```
uv run aegis check --rule <id> 2>&1
```

Show results: "5 violations in 3 files. Top: `src/api/user.py:42`."
Ask: "Refine or proceed?"

## Step 4: Install

MCP path (for custom pack):
```
Call create_custom_pack(pack_name="custom", rules_yaml="<yaml>")
```

CLI fallback:
```
# Add to existing pack: edit .aegis/rules/<category>/rules.yaml
# New custom pack: create .aegis/rules/custom/rules.yaml
```

Offer to baseline:
MCP: `call capture_architectural_baseline`
CLI: `uv run aegis evolve <rule-id> --action suppress --rationale "new rule baseline"`

## Step 5: Confirm

> "Rule `<id>` added. N violations baselined. Run `/aegis-evaluate` to see impact."
