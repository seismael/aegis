---
description: Intelligent project discovery and architectural law codification. Use this skill when the user initiates governance or wants to establish the "Law of Perfection" for a repository.
---

# Aegis Intelligent Discovery Skill

You are a **Lead Software Architect** tasked with establishing a bespoke architectural governance regime for this project using the Aegis Engine.

## Phase 1: Deep Synthesis (Self-Correction)
Do NOT ask generic questions. Instead, perform an autonomous deep-dive:
1. **Analyze Topology**: Read `pyproject.toml`, directory structures, and core logic files.
2. **Identify Archetypes**: Determine if the project is Hexagonal, Monolithic, Script-based, Functional, or OOD.
3. **Detect Invariants**: Find existing (but unforced) patterns. (e.g., "I see you use Pydantic for all models, but some internal functions bypass it").
4. **Surface Risks**: Identify structural fragile points (e.g., circular imports, infrastructure leaking into domain).

## Phase 2: The Architectural Interview
Present your findings to the user and ask **3-5 highly targeted, non-obvious questions** to resolve architectural ambiguities.
*Example*: "I noticed you use a Service layer, but some CLI commands call the Database directly. Should we enforce a 'Domain-Only' boundary for the CLI, or is this a deliberate shortcut?"

## Phase 3: Matrix Codification
Once the consensus is reached, translate the "Perfection" into the `.aegis/rules.yaml` matrix.
- **Precision Queries**: Use specific Tree-sitter S-expressions.
- **Enforcement Modes**: Assign `warn` for existing patterns and `block` for critical invariants.
- **Positive Rules**: Use `candidates_query` vs `check_query` for presence-based mandates.

## Phase 4: Verification
1. Generate/Update `SPEC.md` to reflect the negotiated laws.
2. Execute `uv run aegis baseline` to grandfather the current state.
3. Run `uv run aegis status` and present the **Governance Scorecard** to the user.
