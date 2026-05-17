---
description: Re-evaluate and update existing architectural governance. Use when a project's architecture has evolved or when the user asks to review the current rules.
---

# Aegis Update Skill

You are an expert software architect reviewing an existing Aegis configuration.

## Phase 1: Context Gathering
1. Read `.aegis/rules.yaml` to understand current active rules.
2. Read `.aegis/baseline.json` to understand existing technical debt.
3. Read `.aegis/evolution_log.json` to understand the history of architectural decisions.
4. Explore the repository for new directories, new patterns, or major structural changes.

## Phase 2: Analysis & Proposal
1. Present your findings to the user. E.g., "I noticed you added a new `services/` directory but there are no layering rules governing it."
2. Propose modifications, additions, or removals of rules.
3. Wait for user approval or negotiation.

## Phase 3: Execution
1. Update `.aegis/rules.yaml` with the approved changes.
2. Update `SPEC.md` and `AGENTS.md` to match the new rules.
3. Run `uv run aegis evaluate` and discuss any new violations found.
