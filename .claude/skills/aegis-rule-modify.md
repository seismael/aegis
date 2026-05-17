---
description: Modify an existing architectural rule in Aegis. Use when the user requests a change to a rule's query, scope, severity, or enforcement mode.
---

# Aegis Rule Modify Skill

You are an expert in Tree-sitter and architectural governance.

1. Read `.aegis/rules.yaml` to identify the rule to be modified.
2. Discuss the rationale for the change with the user.
3. Formulate the modifications to the rule (query updates, scope changes, or mode adjustments).
4. Update `.aegis/rules.yaml` accordingly.
5. Update `SPEC.md` if the documentation needs to reflect this change.
6. Run `uv run aegis evaluate` to show the user the new evaluation results.
