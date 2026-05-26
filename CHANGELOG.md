# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-05-26

### Added
- Agent-Native Architectural Microkernel: stateless MCP-only governance.
- 6 MCP tools: `validate_architecture_compliance`, `plan_architecture`,
  `request_semantic_grading_rubric`, `scaffold_governance_framework`,
  `query_knowledge_graph`, `evolve_ruleset`.
- 4 agent chat skills: `/aegis-principal-architect`, `/aegis-init`,
  `/aegis-architect`, `/aegis-semantic-check`.
- `aegis run --headless-check` for CI/Aider `--test-cmd` integration.
- Tri-Core domain architecture: policy, evaluation, observability.
- Re-entrant semantic grading via `build_rubric` delegating to parent LLM.
- JIT rule scoping limiting context to files the agent is actively editing.
- `TelemetryExporterInterface` ABC with `LocalJSONExporter`.
- Agent skills deployed via `importlib.resources` during `aegis install`.
- Auto-generated `AGENTS.md` governance protocol during scaffold.

### Changed
- CLI reduced to `aegis install` and `aegis run` only.
- MCP tools callable natively by agents via `customInstructions` directive.
- Aider integration uses `--test-cmd` + `--auto-test` native self-healing loop.
- `PolicyParser` handles remote policy caching with local fallback.

### Removed
- CLI governance commands: `aegis check`, `aegis apply`, `aegis evolve`,
  `aegis init`, `aegis fix`.
- Git hooks and pre-commit integration.
- Runtime adapters (ClaudeAdapter, AiderAdapter, OpenDevinAdapter).
- DI container (`src/aegis/core/`).
- Domains: Enforcement, Evolution, Governance.
- Virtual File System (V-FS).
- Hardened Tool Proxies (`aegis_write_file`, `aegis_read_file`).

## [0.1.0] - 2026-05-17

### Added
- Initial release of Aegis Architectural Governance Engine.
- Governance Microkernel architecture for polyglot governance.
- Structured rule definition via category-organized rule files.
- Gated enforcement via `aegis check` for CI/CD pipelines.
- Operational skills for context-aware governance discovery and evolution.
- Structural convergence support via `.aegis/baseline.json` debt ledger.
- Automated remediation planning.
- Consensus audit trail.
- MCP Server implementation for universal tool integration.
