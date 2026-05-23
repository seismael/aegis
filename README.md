# Aegis V4 — Agent-Native Architectural Microkernel

Aegis is a **stateless, Agent-Native Architectural Microkernel**. It lives inside Claude and Aider via MCP to mathematically govern autonomous code generation.

## Installation

```bash
pip install aegis
aegis install          # Injects MCP config into ~/.claude.json and ~/.aider.conf.yml
```

That's it. You never run Aegis commands during development.

## Usage

1. Open Claude Code or Aider in any repository.
2. Type `/aegis-init` — the agent discovers your architecture and scaffolds governance rules.
3. Code normally. Before every task completion, the agent automatically calls `validate_architecture_compliance`.
4. If violations exist, the agent remediates natively.

## How It Works

Aegis is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that runs headlessly. The `aegis install` command:

- Writes the MCP server configuration into `~/.claude.json`
- Injects the Governance Directive into Claude's `customInstructions`
- Configures Aider's `--test-cmd` for auto-validate loops

The agent then natively calls Aegis's 6 MCP tools:

| Tool | Purpose |
|------|---------|
| `validate_architecture_compliance` | JIT compliance gate before task completion |
| `request_semantic_grading_rubric` | Re-entrant LLM self-grading for domain language rules |
| `scaffold_governance_framework` | Agent-driven project bootstrap |
| `query_knowledge_graph` | Dependency graphs, workspace hypothesis |
| `evolve_ruleset` | Rule suppression, pack management |
| `plan_architecture` | Pre-emptive JIT rule context before editing |

## Architecture

Tri-Core Microkernel:

- **Policy** — Rule definitions, YAML parser, pack manager
- **Evaluation** — Tree-sitter AST, Graph, Regex analyzers, JIT scoping, baseline
- **Observability** — Telemetry recording, local JSON + OTLP export

Aegis is **100% stateless**. It does not maintain sessions, history, or memory. It relies entirely on the parent agent's context window and project knowledge systems.

## Enterprise

- Telemetry exports to `.aegis/telemetry.json` by default
- OTLP gRPC exporter available for Datadog/Grafana
- Plugin system for custom evaluation engines
- 15+ rule packs: architecture, security, best-practices, testing, and more

## License

Apache 2.0
