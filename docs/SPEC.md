## V4 Agent-Native Invariants

### Mandatory Compliance Check

Before declaring ANY coding task complete, the AI agent MUST:

1. Call `validate_architecture_compliance` with the list of modified files.
2. If violations are returned, remediate the code natively.
3. Re-run validation until SUCCESS is returned.

### No Direct File System Governance

Aegis V4 never:
- Installs git hooks
- Watches file system events
- Intercepts file reads/writes
- Maintains session state

# Aegis V4: Agent-Native Technical Specification

## Layer 0: The Workspace Initializer
Aegis provides a local initialization layer that binds into your specific development workspace.
- **Universal Command**: `aegis init`
- **Action**: Creates local `mcp.json`, `.claude.json` (MCP server + customInstructions) and `.aider.conf.yml` (MCP server + test-cmd) in the project root.
- **Invariant**: The initialization is completely local and non-invasive. It does not modify global dotfiles.

## Layer 1: The Tri-Core Microkernel

### Policy Domain
Rule definitions, YAML parsing, and pack management. Translates `.aegis/rules/` into structured, evaluable models.
- **Pack Manager**: Installs, removes, and resets rule packs from bundled resources.
- **Parser**: Loads YAML rules into Pydantic `Rule` models with multi-engine routing.

### Evaluation Domain
Dispatches structural analysis to specialized engines. JIT-scopes rules to the files the agent is actively editing.
- **AST (Tree-sitter)**: Language-aware structural analysis.
- **Graph**: Cross-file dependency and coupling analysis.
- **Regex**: High-speed pattern matching for secrets and simple invariants.
- **Semantic**: Re-entrant LLM grading rubrics for domain language rules.
- **Baseline**: Technical debt ledger (`.aegis/baseline.json`) with thread-safe atomic writes.
- **Plugins**: Custom evaluation engines implementing `EvaluationEngineInterface`.

### Observability Domain
- **Telemetry Recorder**: Persists check/remediation events to `.aegis/telemetry.json`.
- **OTLP Exporter**: Opt-in gRPC streaming for Datadog/Grafana enterprise observability.

## Layer 2: The MCP Tool Surface (Core & Skills)

### 2.1 Core Governance Tools
| Tool | Purpose |
|------|---------|
| `validate_architecture_compliance` | JIT compliance gate — evaluates modified files, returns SUCCESS or violation report |
| `request_semantic_grading_rubric` | Re-entrant LLM self-grading rubric for domain language rules |
| `plan_architecture` | Pre-emptive task alignment — returns JIT-scoped rules for intent + file |

### 2.2 Agent-Native "On-Demand" Skills (Higher-Level)
These skills wrap complex core operations into intuitive, project-wide commands for the agent.

| Skill | Purpose |
|-------|---------|
| `discover_architectural_patterns` | Scans workspace, detects frameworks, and proposes new governance laws |
| `apply_governance_law` | Formally adopts a rule pack or custom law; manages project-wide YAML generation |
| `request_exception` | Petitions for a documented exception to a law; records debt in `baseline.json` |
| `generate_health_scorecard` | (Re)generates the root `AEGIS.md` dashboard for agent/human visibility |

## Layer 3: The Agent-Native Execution Guarantee

Aegis V4 enforces governance through the agent's native tool execution loop:
- **Agent Entry Point (`AEGIS.md`)**: A root-level scorecard that onboards entering agents by listing active laws, pending proposals, and current health score.
- **Claude Code**: Governance Directive in `customInstructions` + `.claude.md`.
- **Aider**: Native self-healing loop via `--test-cmd`.
- **Gemini CLI**: `GEMINI.md` integration.
- **Cross-Agent Memory**: Coordination via `.aegis/session.json`.

## Layer 4: Active Rule Matrix
- Bundled rule packs in `src/aegis/resources/default_rules/` (18 packs: architecture, security, testing, and more).
- Installed rules live in `.aegis/rules/`.
- JIT scoping filters to a maximum of 15 relevant rules per validation call.
