---
description: Modify an existing architectural rule in Aegis. Use when the user requests a change to a rule's query, scope, severity, or enforcement mode.
---

# Aegis Rule Modify Skill

You are an expert in architectural governance, Tree-sitter, and the Aegis evolution protocol.

1. Read `.aegis/rules.yaml` to identify the rule to be modified.
2. Discuss the rationale for the change with the user. The user must provide a clear justification.
3. **Before modifying the rule**, append an `EvolutionDecision` entry to `.aegis/evolution_log.json` recording the user's rationale, the rule ID, and the action being taken (`relax_rule`, `suppress`, or `refactor_required`). This maintains an auditable paper trail of why the architecture changed.
4. Formulate the modifications to the rule (query updates, scope changes, mode adjustments, or engine_type changes).
5. Update `.aegis/rules.yaml` accordingly.
6. **Update `SPEC.md`:** Document the rule modification and its rationale, including the date and consensus action taken.
7. Run `uv run aegis evaluate` to show the user the new evaluation results and verify no unexpected side effects.
