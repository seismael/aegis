# Aegis Target Specification

## L1: The Aegis Governance Engine
Aegis is a localized microkernel for the **Negotiation** and **Enforcement** of architectural invariants. Supports 3 evaluation engines: tree-sitter (AST), graph (cross-file dependency), and regex (pattern matching).

## L2: Domain Decomposition (Execution Engine)
- **Policy Domain**: Structured YAML-to-Rule parsing. Supports EngineType routing, per-rule excludes, and positive/negative rule queries.
- **Evaluation Domain**: AST analysis, regex pattern analysis, cross-file dependency graph analysis. Multi-engine dispatch with `_filter_excluded` for per-rule path exclusion.
- **Enforcement Domain**: Gating decisions, remediation prompt synthesis, and CI/CD integration.
- **Evolution Domain**: Consensus logging (`evolution_log.json`), decision persistence, and architectural debt ledger (`baseline.json`).

## L3: Authoring Layer (AI Skills)
All architectural laws are discovered and codified via **AI Skills** located in `.claude/skills/`. This allows for natural language negotiation of perfection.
- `aegis-init` — 3-state initialization protocol (Detection → Interview Loop → Compilation)
- `aegis-rule-add` — Rule authoring with MCP auto-evaluation
- `aegis-rule-modify` — Rule evolution with auditable rationale logging
- `aegis-evaluate` — Scorecard rendering with baseline comparison

## L4: Active Rules
See `.aegis/rules.yaml` for the machine-parseable source of truth.

### Current Rules (6 total, 0 baselined debt)
| ID | Engine | Severity | Mode | Scope |
|---|---|---|---|---|
| strict-ood | tree-sitter | HIGH | block | src/ except cli/ |
| hexagonal-isolation | tree-sitter | HIGH | block | domain/ except container,kernel,tests |
| no-circular-deps | graph | HIGH | block | all py |
| required-docstrings | tree-sitter | MEDIUM | report | all py |
| no-print-statements | regex | MEDIUM | warn | src/ except tests,cli,installer |
| no-wildcard-imports | regex | MEDIUM | warn | all py |
