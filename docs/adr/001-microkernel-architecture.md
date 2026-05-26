# ADR 001: Tri-Core Agent-Native Microkernel Architecture

## Status
Accepted

## Context
Aegis V4 must be a stateless, agent-native governance engine. The V3 approach of OS-level hooks (git hooks, file watchers, runtime adapters) created friction between the human developer and the AI agent. Governance should feel native to the agent's cognition loop, not bolted on as system middleware.

## Decision
We adopted a **Tri-Core Agent-Native Microkernel** architecture:

### Core (Microkernel / MCP Surface)
`server.py` is the single entry point. It initializes all domain services via constructor injection, registers 6 MCP tools, 4 resources, and 4 prompts, and serves as the stateless orchestrator. No DI container.

### Policy Domain
Translates `.aegis/rules/*.yaml` into structured `Rule` models. Handles pack management (install/remove/reset via `importlib.resources`), rule parsing, and multi-engine routing.

### Evaluation Domain
Dispatches analysis to specialized engines (regex, AST/tree-sitter, graph, semantic). Implements JIT scoping for the files the agent is actively editing. Manages the baseline debt ledger (`.aegis/baseline.json`) with thread-safe atomic writes. Supports plugin-based custom analyzers via `EvaluationEngineInterface`.

### Observability Domain
Records check/remediation events to `.aegis/telemetry.json` via a `TelemetryExporterInterface` abstraction. Local JSON is the default; OTLP gRPC export is supported through the same interface for enterprise use.

## Agent Native Pattern
- No git hooks. No file watchers. No OS-level middleware.
- Agents connect via MCP stdio (`aegis run`).
- Claude: `customInstructions` directive mandates `validate_architecture_compliance` before task completion.
- Aider: `--test-cmd aegis run --headless-check` + `--auto-test` creates native self-healing loop.
- Skills (`/aegis-init`, `/aegis-architect`, etc.) are deployed to agent directories via `importlib.resources`.

## Consequences
- **Pros**: Zero OS friction, agent-native UX, deterministic rule evaluation, JIT context efficiency, stateless (no session memory).
- **Cons**: Requires one-time `aegis install` CLI step; MCP server must be running during agent sessions.
