---
description: First-time setup for Aegis Universal Architectural Governance. Use this skill when the user wants to establish project governance or migrate to the Aegis engine.
---

# Aegis Init Skill

You are an expert software architect facilitating the adoption of the Aegis Governance Engine.

## Phase 1: Context Discovery
1. Analyze the project structure, `pyproject.toml`, and core source files to identify the archetype (e.g., FastAPI, Django, React, Rust CLI).
2. Identify primary languages and known architectural patterns in use.
3. Discuss the project's quality mandates with the user.

## Phase 2: Matrix Generation
1. Formulate the logical constraint matrix in `.aegis/rules.yaml`.
2. Map rules to specific languages using the `language` field (e.g., `py`, `ts`, `rs`).
3. Use `candidates_query` and `check_query` for positive enforcement (e.g., "Every service must have a unit test").
4. Default to `warn` mode for new rules to ensure a non-destructive rollout.

## Phase 3: Documentation & Gating
1. Update `SPEC.md` and `AGENTS.md` to reflect the new protocol.
2. Run `uv run aegis baseline` to grandfather existing debt.
3. Run `uv run aegis status` to verify the active matrix.
