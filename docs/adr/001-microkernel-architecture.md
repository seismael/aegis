# ADR 001: Tri-Core Agent-Native Microkernel Architecture

## Status
Accepted

## Context
Aegis V4 must be a stateless, agent-native governance engine. The V3 approach of OS-level hooks (git hooks, file watchers, runtime adapters) created friction between the human developer and the AI agent. Governance should feel native to the agent's cognition loop, not bolted on as system middleware.

## Decision
We adopted a **Tri-Core Agent-Native Microkernel** architecture:

### Core (Microkernel / MCP Surface)
`server.py` is the single entry point. It initializes all domain services via constructor injection, registers 6 MCP tools, 4 resources, and 4 prompts, and serves as the stateless orchestrator.

### Policy Domain
Translates `.aegis/rules/*.yaml` into models. Handles the **Universal Harness** system, allowing native injection into Claude, Aider, and Gemini.

### Evaluation Domain
Dispatches analysis to specialized engines:
- **Polyglot AST**: Structural analysis.
- **Import Graph**: $O(1)$ JIT-cached dependency checks.
- **Hardened Semantic**: Mandatory re-entrant rubrics for LLM self-evaluation.

### Coordination Domain (New)
Introduces the **Cross-Agent Session Manager**. While the kernel remains stateless relative to the OS, it leverages `.aegis/session.json` to facilitate technical handoffs between different AI agents working on the same repository.

---

## Agent Native Pattern
- No OS friction. No git hooks.
- Agents connect via MCP stdio (`aegis run`).
- **Claude**: `customInstructions` + `.claude.md`.
- **Gemini**: `GEMINI.md` integration.
- **Aider**: Self-healing loops via `--test-cmd`.

## Consequences
- **Pros**: Seamless agent UX, deterministic structural evaluation, efficient context usage, coordinated multi-agent workflows.
- **Cons**: Requires one-time `aegis install` setup.
