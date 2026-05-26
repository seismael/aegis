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

## Layer 0: The Universal Bootstrapper
Aegis provides a global installation layer that binds into your development toolchain.
- **Universal Command**: `aegis install`
- **Action**: Mutates `~/.claude.json` (MCP server + customInstructions) and `~/.aider.conf.yml` (MCP server + test-cmd).
- **Invariant**: The installer is idempotent and project-agnostic. Run once per machine.

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

## Layer 2: The MCP Tool Surface (6 Tools)

| Tool | Purpose |
|------|---------|
| `validate_architecture_compliance` | JIT compliance gate — evaluates modified files, returns SUCCESS or violation report |
| `request_semantic_grading_rubric` | Re-entrant LLM self-grading rubric for domain language rules |
| `scaffold_governance_framework` | Agent-driven project bootstrap — writes rule packs to `.aegis/rules/` |
| `query_knowledge_graph` | Dependency graphs, workspace hypothesis, module health |
| `evolve_ruleset` | Rule suppression, pack install/remove, baseline management |
| `plan_architecture` | Pre-emptive task alignment — returns JIT-scoped rules for intent + file |

## Layer 3: The Agent-Native Execution Guarantee

Aegis V4 enforces governance through the agent's native tool execution loop:
- **Claude Code**: Governance Directive injected into `customInstructions` makes validation mandatory before task completion.
- **Aider**: `--test-cmd` and `--auto-test` flags create a native self-healing loop.
- **No OS hooks**: No git hooks, no file watchers, no I/O middleware.
- **Stateless**: Aegis has no session memory. The parent agent's context window holds state.

## Layer 4: Active Rule Matrix
- Bundled rule packs in `src/aegis/resources/default_rules/` (18 packs: architecture, security, testing, and more).
- Installed rules live in `.aegis/rules/`.
- JIT scoping filters to a maximum of 15 relevant rules per validation call.
