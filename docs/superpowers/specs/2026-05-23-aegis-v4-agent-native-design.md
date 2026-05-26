# Aegis V4 Agent-Native Architectural Microkernel — Design Spec

**Status:** Approved  
**Date:** 2026-05-23  
**Approach:** Surgical In-Place Refactoring (Approach A)

---

## 1. Vision

Transform Aegis from a CLI-centric system tool into a 100% Agent-Native microkernel. Aegis lives entirely within AI coding agents (Claude, Aider) via MCP, serving as a stateless mathematical rule router and deterministic AST parser.

**Core Principles:**
- No human-facing CLI during daily development
- No OS git hooks — agent tools natively loop via `customInstructions` / `--test-cmd`
- No stateful session management — agent context window handles memory
- Re-entrant semantic grading: Aegis sends rubrics back to the parent LLM
- JIT scoping: dynamically filters rules to the files the agent is actively editing

---

## 2. Target Architecture — Tri-Core Microkernel

```
src/aegis/
├── __init__.py
├── cli/
│   ├── __init__.py
│   └── main.py                     # install + run only (~50 lines)
├── kernel/
│   ├── __init__.py
│   ├── models.py                   # MCP request/response Pydantic schemas
│   ├── server.py                   # FastMCP microkernel with 6 tools
│   └── errors.py                   # MCP error protocol (from domain/enforcement)
├── domain/
│   ├── __init__.py
│   ├── policy/
│   │   ├── __init__.py
│   │   ├── models.py               # Rule, RuleCategory, Severity, EngineType
│   │   ├── parser.py               # YAML → Rule domain objects
│   │   ├── pack.py                 # RulePackMeta, InstalledPack, PackManifest
│   │   ├── pack_manager.py         # Install/remove/reset rule packs from resources
│   │   └── config.py               # AegisConfig model (from core/models/config.py)
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── ports.py                # ArchitecturalViolation, analyzer interfaces
│   │   ├── service.py              # Orchestrates analyzers per file/phase
│   │   ├── scoping.py              # JIT rule filtering by file (applies_to/excludes)
│   │   ├── baseline.py             # Technical debt ledger (baseline.json)
│   │   ├── prompt_synthesizer.py   # Violations → agent remediation prompts
│   │   ├── constants.py            # IGNORE_DIRS, LANG_EXT_MAP (from core)
│   │   ├── analyzers/
│   │   │   ├── __init__.py
│   │   │   ├── regex.py            # Regex pattern matching
│   │   │   ├── ast.py              # Tree-sitter AST queries
│   │   │   ├── graph.py            # Import dependency graph analysis
│   │   │   └── semantic.py         # Re-entrant LLM grading rubrics
│   │   └── plugins/
│   │       ├── __init__.py
│   │       ├── interfaces.py       # EvaluationEngineInterface (simplified)
│   │       └── registry.py         # Dynamic .aegis/plugins/ loading
│   └── observability/
│       ├── __init__.py
│       ├── telemetry.py            # TelemetryRecorder + TelemetryExporterInterface
│       └── exporters/
│           ├── __init__.py
│           ├── local.py            # .aegis/telemetry.json
│           └── otlp.py             # OTLP gRPC streaming
├── infrastructure/
│   ├── __init__.py
│   └── installer.py                # AgentNativeInstaller (Claude + Aider only)
└── resources/                       # Bundled resources (rules, skills)
    ├── __init__.py
    ├── default_rules/              # 18 rule packs in subdirectories
    └── skills/
        ├── aegis-principal-architect.md
        ├── aegis-init.md           # Agent project bootstrap
        ├── aegis-architect.md      # Rule generation protocol
        └── aegis-semantic-check.md # Domain language self-grading
```

### Deleted

| Path | Reason |
|------|--------|
| `domain/evolution/` | Stateful audit trail — agent context handles memory |
| `domain/enforcement/` | Enforcement = prompt synthesis now; fixer deleted |
| `domain/governance/` | Middleman orchestrator — server.py orchestrates directly |
| `domain/evaluation/vfs.py` | Stateless kernel — agents use native file tools |
| `infrastructure/adapters/` | MCP is universal, no dialect translation needed |
| `infrastructure/file_watcher.py` | OS-level file watching — agent tools handle natively |
| `infrastructure/git_provider.py` | Git hook diffing — no OS git integration in V4 |
| `core/` | DI container replaced by constructor injection in server.py |
| `.pre-commit-config.yaml` | No git hooks in V4 |

### MCP Tool Surface (6 Tools)

| Tool | Domain | Purpose |
|------|--------|---------|
| `validate_architecture_compliance` | evaluation | Core compliance gate — evaluates modified files with JIT scoping |
| `request_semantic_grading_rubric` | evaluation | Re-entrant LLM rubric for domain language rules |
| `scaffold_governance_framework` | policy | Agent-driven project bootstrap (writes .aegis/) |
| `query_knowledge_graph` | evaluation | Dependency graph, workspace hypothesis, module health |
| `evolve_ruleset` | policy | Manage rules/baseline/packs (suppress, install, remove) |
| `plan_architecture` | evaluation + policy | Pre-emptive task alignment — JIT rules for intent + file |

### MCP Resources (4)

| Resource URI | Content |
|-------------|---------|
| `aegis://rules` | All active rule definitions |
| `aegis://baseline` | Technical debt ledger |
| `aegis://context/{path}` | Ambient rules for a specific file path |
| `aegis://spec` | SPEC.md contents for agent handoff |

### MCP Prompts (4)

| Prompt | Purpose |
|--------|---------|
| `evaluate-architecture` | Template for validate_architecture_compliance call |
| `remediate-violations` | Template for consuming violation report |
| `initialize-governance` | Template for /aegis-init flow |
| `inspect-dependency` | Template for dependency graph queries |

---

## 3. Phase-by-Phase Execution

### Phase 1: Core Purge & Protocol Lock (Days 1-2)

**Goal:** Strip the old paradigm. Delete dead code. Lock in the FastMCP microkernel contract.

**CLI Reduction (`src/aegis/cli/main.py`):**
- Delete all command methods except `install()` and `run()`
- Delete `_rules_app`, `_plugin_app` properties and all subcommands
- Replace `_register_commands()` with direct `install` + `run` registration
- Remove `rich` imports — no human-facing output
- Remove `_require_governance()`, `_warn_degraded()`

**Domain Purge (Delete entire directories):**
- `src/aegis/domain/evolution/`
- `src/aegis/domain/enforcement/` (except prompt_synthesizer content)
- `src/aegis/domain/governance/`
- `src/aegis/domain/evaluation/vfs.py`
- `src/aegis/infrastructure/adapters/` (all 5 files)
- `src/aegis/infrastructure/file_watcher.py`
- `src/aegis/infrastructure/git_provider.py`
- `src/aegis/core/`

**Relocations:**

| From | To |
|------|-----|
| `domain/enforcement/remediation.py` | `domain/evaluation/prompt_synthesizer.py` |
| `domain/enforcement/errors.py` | `kernel/errors.py` |
| `infrastructure/regex_analyzer.py` | `domain/evaluation/analyzers/regex.py` |
| `infrastructure/ast_analyzer.py` | `domain/evaluation/analyzers/ast.py` |
| `infrastructure/graph_analyzer.py` | `domain/evaluation/analyzers/graph.py` |
| `infrastructure/semantic_analyzer.py` | `domain/evaluation/analyzers/semantic.py` |
| `core/plugins/` | `domain/evaluation/plugins/` |
| `core/models/config.py` | `domain/policy/config.py` |
| `core/constants.py` | `domain/evaluation/constants.py` |

**Server Refactoring:** Replace `Container` DI with explicit constructor injection in `server.py`. Every `AegisKernel` dependency passed at init time.

**Test Suite:**

| Action | Files |
|--------|-------|
| Delete | `test_evolution_service.py`, `test_fixer.py`, `test_file_watcher.py`, `test_git_provider.py`, `test_adapters.py`, `test_vfs.py`, `test_v3_jailbreak.py`, `test_governance_service.py` |
| Refactor | `test_cli.py` (install + run only), `test_container.py` (simplified init), all survivors update import paths |
| Keep | `test_rule_model.py`, `test_rule_pack_*`, `test_policy_parser.py`, `test_evaluation_*`, `test_scoping.py`, `test_phase_filtering.py`, `test_baseline.py`, `test_regex_analyzer.py`, `test_ast_analyzer.py`, `test_graph_analyzer.py`, `test_plugin_*.py` (5), `test_telemetry.py`, `test_mcp_*.py` (5), `test_errors.py`, `test_config_model.py`, `test_integration.py` |
| Rename | `test_remediation_synthesizer.py` → `test_prompt_synthesizer.py` |

**Package Updates:**
- `pyproject.toml`: remove `gitpython`, `watchfiles` deps; remove extra entry points
- Delete `.pre-commit-config.yaml`
- Update `mcp.json` and `config.toml` to use `aegis run`

**Phase 1 Gate:** `ruff check` passes, `pytest --timeout=60` all green, `aegis install` runs, net ~8,000 LOC deleted.

---

### Phase 2: Agent-Native Installer + JIT Scoping (Days 3-4)

**AgentNativeInstaller (`infrastructure/installer.py`):**
- `_inject_claude()`: writes to `~/.claude.json` — adds `mcpServers.aegis` entry and appends AEGIS_GOVERNANCE_DIRECTIVE to `customInstructions`
- `_inject_aider()`: writes to `~/.aider.conf.yml` — adds MCP server line and `--test-cmd` / `--auto-test` flags
- No other adapters. MCP is the universal protocol.

**JIT Scoping (`scoping.py` — `get_relevant_rules`):**
- Input: list of file paths, all rules from `.aegis/rules/`
- Filter: `applies_to` glob match, `excludes` negation, `language` extension match
- Sort: severity desc, then rule specificity
- Cap: 15 rules max to prevent context collapse
- Adjacency bonus: rules targeting files in same import graph neighborhood get priority

**validate_architecture_compliance:**
- Calls scoping engine for files_modified
- Runs AST/Graph/Regex analyzers on filtered rules
- Applies baseline exemptions (never for SECURITY rules)
- Returns `"SUCCESS: Architecture compliant."` or formatted violation report with remediation instructions

**scaffold_governance_framework:**
- Called by agent via `/aegis-init` skill
- Copies default rule packs from `importlib.resources` to `.aegis/rules/`
- Returns list of installed packs

**query_knowledge_graph:**
- `dependency_graph`: returns import graph for a module
- `module_health`: returns violation counts per module
- `hypothesis`: scans pyproject.toml/package.json, detects frameworks, proposes tier structure

**Phase 2 Gate:** `install` + `run` + MCP tool call roundtrip tests all pass.

---

### Phase 3: Re-entrant Semantic Grading (Days 5-6)

**request_semantic_grading_rubric:**
- Detects SEMANTIC engine rules for target file
- Builds LLM-evaluable rubric in markdown format
- Rubric includes rule description, expected domain terms, anti-patterns to check
- Agent reads rubric, grades its own code, applies fixes natively

**Skills:**
- `/aegis-init.md`: agent calls `query_knowledge_graph(hypothesis)` → presents architecture to user → calls `scaffold_governance_framework`
- `aegis-architect.md`: updated for V4 lifecycle (init → plan → code → validate → remediate loop)

**Prompt Templates:**
- `initialize-governance`: guides agent through `/aegis-init`
- `evaluate-architecture`: guides agent through validation
- `remediate-violations`: guides agent through fixing violations
- `inspect-dependency`: guides agent through dependency analysis

**Phase 3 Gate:** semantic rubric roundtrip test + skill-driven bootstrap integration test pass.

---

### Phase 4: Documentation Overhaul (Day 7)

**README.md:**
- Delete CLI reference tables, `aegis check --staged` examples, git hook instructions
- Rewrite: "Aegis is a stateless, Agent-Native Architectural Microkernel. It lives inside Claude and Aider via MCP to mathematically govern autonomous code generation."
- Installation: `aegis install` (once), then `/aegis-init` in chat

**ARCHITECTURE.md:**
- V4 Symbiotic Model: why no git hooks, how Aegis leverages parent LLM for memory/semantic analysis
- Tri-Core diagram (Policy → Evaluation → Observability)
- Installer as sole bridge between host and agent ecosystem

**SPEC.md:**
- Updated invariants forcing `validate_architecture_compliance` before task completion
- Agent must remediate if violations returned

**OPERATIONS.md:**
- Reading `.aegis/telemetry.json` for governance health
- OTLP export configuration
- SSE server deployment options

---

### Phase 5: CI/CD & Distribution (Days 8-9)

**Packaging:**
- `importlib.resources` for rule packs and skills in PyPI wheel
- Single entry point: `aegis = "aegis.cli.main:entry_point"`

**GitHub Actions:**
- Replace `aegis check` with MCP integration test (start server → call validate → assert SUCCESS)
- Keep `ruff check` + `pytest` gates

**Telemetry:**
- Local JSON exporter stable
- OTLP gRPC exporter for enterprise Datadog/Grafana
- Generic `TelemetryExporterInterface` unchanged

---

## 4. Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Import breakage during relocation | Single-module moves per commit; tests gate every commit |
| Agent fails to call MCP tools | `customInstructions` injection makes it mandatory; skills reinforce |
| Context collapse from too many rules | JIT scoping caps at 15 rules; adjacency bonus prioritises |
| Enterprise needs custom rules | Plugin system survives in evaluation domain: `EvaluationEngineInterface` |
| Lost configuration during purge | `baseline.json` and `.aegis/config.yaml` structure unchanged |
