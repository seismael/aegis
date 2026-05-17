---
description: Add a new architectural rule to Aegis. Use when the user requests a new structural constraint or convention.
---

# Aegis Rule Add Skill

You are an expert in Tree-sitter and architectural governance.

1. Read `.aegis/rules.yaml` to understand existing rules and conventions.
2. Ask clarifying questions to pinpoint the exact structural invariant the user wants to enforce.
3. Formulate the Tree-sitter query. For positive rules (must have X), define a `candidates_query` and a `check_query`.
4. Suggest a severity (LOW, MEDIUM, HIGH, CRITICAL) and an enforcement mode (`silent`, `report`, `warn`, `block`, `fix`). Suggest `warn` for new rules to avoid immediate CI breakages.
5. Identify the scope (`applies_to`, `excludes`) and language.
6. Once agreed, append the rule to `.aegis/rules.yaml`.
7. Update `SPEC.md` if the documentation needs to reflect this new rule.
8. Run `uv run aegis evaluate` to show the user any immediate violations caused by the new rule.
