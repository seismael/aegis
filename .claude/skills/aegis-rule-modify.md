---
description: Modify an existing architectural rule with impact prediction. Use this skill when the user requests a change to a rule's logic, scope, or severity.
---

# Aegis Impact-Aware Evolution Skill (Modify)

You are an expert in **Structural Refactoring** and **Tree-sitter**. Your goal is to modify existing architectural laws without causing unmanaged chaos.

## Phase 1: Impact Prediction
Before applying any change to `.aegis/rules.yaml`:
1. **Analyze Current State**: Run an evaluation with the *proposed* rule logic against the full workspace.
2. **Quantify the Delta**: "The current version has 5 violations. The new version will create **12 additional violations** across 4 modules."
3. **Present a "Pre-flight Report"**: Show the user exactly which files will be blocked if they proceed with this modification.

## Phase 2: Negotiated Modification
Ask the user to confirm the transition strategy based on the impact report:
- **Pragmatic Path**: "Should we grandfather these new violations into the baseline automatically?"
- **Strict Path**: "Should we block all changes until these new violations are refactored?"
- **Gradual Path**: "Should we start the modified rule in `warn` mode first?"

## Phase 3: Consensus & Log
1. Update `.aegis/rules.yaml` with the approved modification.
2. Update `SPEC.md` and `AGENTS.md` documentation.
3. Record the decision, rationale, and user consensus in `evolution_log.json` via the `aegis evolve` command.
4. Run `uv run aegis status` to confirm the matrix is updated and healthy.
