---
description: First-time setup for Aegis Architectural Governance. Use this skill when the user runs aegis init or wants to establish project governance for the first time.
---

# Aegis Init Skill

You are an expert software architect helping a team establish their architectural governance using the Aegis engine.

## Phase 1: Explore & Interview
1. Read the repository structure, `pyproject.toml`, and sample source code files to understand the project archetype (e.g., FastAPI, Django, CLI, Hexagonal).
2. Ask the user about their architectural goals, known pain points, and specific conventions they want to enforce. Wait for their response.

## Phase 2: Generate Rules
1. Based on the conversation and your analysis, generate a set of architectural rules.
2. Write these rules to `.aegis/rules.yaml`.
3. Example rule format:
```yaml
rules:
  - id: strict-ood
    description: Loose procedural functions are forbidden.
    severity: HIGH
    mode: warn
    language: py
    query: |
      (module [(function_definition) (decorated_definition)] @violation)
```
*Note: Start with conservative modes like `warn` or `report` so as not to block the team immediately.*

## Phase 3: Document & Validate
1. Generate `SPEC.md` documenting these rules in a human-readable format.
2. Run `uv run aegis evaluate` to show the user the initial impact.
3. Offer to run `uv run aegis baseline` to grandfather existing violations.
