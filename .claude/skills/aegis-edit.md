---
description: Real-time governance during code editing. Get context before editing, validate mid-thought, verify after writing.
---

# Aegis Edit — Real-Time Governance Loop

You are an architectural compliance monitor. Run this loop for every file edit.

## Phase 1: Pre-edit context

Before writing a single line of code:

MCP path:
```
Call get_active_context("src/target/file.py")
→ Returns structured JSON: rules[] with id, description, severity, mode, rationale
```

CLI fallback:
```
uv run aegis check --rule <rule-id> -- applies_to matches
```

You should know which rules apply to the file BEFORE you start editing. Pay special attention to BLOCK-level rules — they will reject your changes.

If there are 3+ active rules for the file, brief yourself:
> "Editing `src/domain/order.py`. 4 active rules: `arch-layer-violation` (BLOCK), `arch-no-print` (warn), `naming-convention` (report), `required-docstrings` (warn)."

## Phase 2: Mid-thought validation

When you draft code but haven't written it to disk yet:

MCP path:
```
Call evaluate_code_delta(code_string="def f(): ...", language="py")
→ Returns structured JSON: passed (bool), violations[]
```

CLI fallback: not available — this is MCP-only functionality.

If `passed: false`, examine `violations[]` and fix before writing. Each violation has `line`, `rule_id`, `severity`, `description`.

Example reaction to a violation:
> "`evaluate_code_delta` returned a BLOCK violation: `arch-layer-violation` at line 3. My code imports infrastructure from domain. Restructuring to use dependency inversion."

## Phase 3: Post-write verification

After writing the file:

MCP path:
```
Call validate_architecture_compliance(staged_only=True)
→ Returns structured JSON: passed (bool), violations[]
```

CLI fallback:
```
uv run aegis check --staged 2>&1
```

If violations found, fix them and re-validate. Loop until `passed: true` or user intervenes.

## Phase 4: Commit summary

When asked to commit, summarize governance state:

> **Governance status**: clean
> Rules checked: 92
> Files edited: 3 (src/domain/order.py, src/api/order_routes.py)
> Blocking violations: 0
> Pre-commit validation: passed
