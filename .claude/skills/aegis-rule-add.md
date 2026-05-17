---
description: Add a new architectural rule to Aegis. Use when the user requests a new structural constraint or convention.
---

# Aegis Rule Add Skill

You are an expert in architectural governance, Tree-sitter, and the Aegis MCP engine.

1. Read `.aegis/rules.yaml` to understand existing rules and conventions.
2. Ask clarifying questions to pinpoint the exact structural invariant the user wants to enforce.
3. Formulate the rule. For Tree-sitter rules, define the S-expression query. For positive rules (must have X), define a `candidates_query` and a `check_query`. For cross-file or pattern rules, set `engine_type` to `graph` or `regex` accordingly.
4. Suggest a severity (LOW, MEDIUM, HIGH, CRITICAL) and an enforcement mode (`silent`, `report`, `warn`, `block`). Suggest `warn` for new rules to avoid immediate CI breakages.
5. Identify the scope (`applies_to`, `excludes`) and language.
6. Once agreed, append the rule to `.aegis/rules.yaml`.
7. **Use the MCP `validate_architecture_compliance` tool** (with `staged_only=false`) to auto-evaluate the new rule's impact on the existing codebase. Present the results to the user.
8. **Update `SPEC.md`:** Document the new L2 container boundary affected by this rule.
9. Conclude by running `uv run aegis status` to verify the active matrix.
