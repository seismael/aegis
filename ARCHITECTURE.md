# Aegis V4 Architecture

## The Symbiotic Model

Aegis V4 is a purely Agent-Native microkernel. It does not run on the operating system — it runs inside AI coding agents via MCP.

### Why No Git Hooks

V3 used `.pre-commit-config.yaml` and `.git/hooks/pre-commit` to enforce governance. V4 eliminates this entirely:

- Claude receives the Governance Directive in `customInstructions`, making validation mandatory before task completion.
- Aider loops against `aegis run --check` via `--test-cmd`, creating a native self-healing cycle.
- The agent, not the OS, enforces governance.

### How Aegis Leverages the Parent LLM

Aegis is a **deterministic** kernel:

- **AST/Graph/Regex analyzers** — Pure Python math. No LLM calls.
- **Semantic rules** — Aegis returns a grading rubric. The parent LLM self-evaluates.
- **Memory** — Aegis has none. The agent's context window holds session state.
- **Evolution** — SPEC.md and agent project knowledge capture architectural decisions.

### Tri-Core Microkernel

```
Agent (Claude/Aider)
  |
  ├── plan_architecture()
  ├── validate_architecture_compliance()
  ├── request_semantic_grading_rubric()
  |
  v
+-----------------------------------+
|         FastMCP Server             |
|                                    |
|  +------------+  +------------+    |
|  |   Policy    |  | Evaluation |    |
|  |  Packs      |  | Analyzers  |    |
|  |  Parser     |  | Scoping    |    |
|  |  Models     |  | Baseline   |    |
|  +------------+  +------------+    |
|                                    |
|  +------------+                     |
|  |Observability|                    |
|  | Telemetry   |                    |
|  | Exporters   |                    |
|  +------------+                     |
+-----------------------------------+
```

### The Installer

`aegis install` is the sole bridge between the host machine and the agent ecosystem:

- Mutates `~/.claude.json` (MCP server + customInstructions)
- Mutates `~/.aider.conf.yml` (MCP server + test-cmd + auto-test)
- No other tool-specific code exists at runtime

### Design Decisions

See `docs/adr/001-microkernel-architecture.md` for the original microkernel ADR.
