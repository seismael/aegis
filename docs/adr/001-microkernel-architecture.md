# ADR 001: V4 Agent-Native Microkernel Architecture

## Status
Accepted

## Context
Aegis V4 must be a stateless, agent-native governance engine. The V3 approach of OS-level hooks (git hooks, file watchers, runtime adapters) created friction between the human developer and the AI agent. Governance should feel native to the agent's cognition loop, not bolted on as system middleware. Furthermore, the installation process must be completely agnostic, non-intrusive, and invisible to projects that are not actively governed.

## Decision
We adopted a **V4 Agent-Native Microkernel** architecture utilizing a **Global Hook / Local Activation** pattern:

### Core (Microkernel / MCP Surface)
`server.py` is the single entry point. It initializes all domain services via constructor injection, registers 10 MCP tools, and serves as the stateless orchestrator. State is never preserved in daemon memory; it lives entirely within the AI agent's context window and the `.aegis/` state directory.

### Global Hook / Local Activation (Option C)
- **Global Hook**: The `aegis-kernel` MCP server is registered directly into the user's global configuration files (`~/.claude.json`, `~/.gemini.json`, `~/.aider.conf.yml`).
- **Local Activation**: When an AI agent launches the MCP server in a project directory, the kernel inspects the workspace. If an `.aegis/` folder is present, it registers its 10 tools. If `.aegis/` is missing, the server goes to sleep, returning 0 tools to the agent. This ensures Aegis never pollutes ungoverned workspaces.

### Dual-Layer Directives
- **Global**: Only the raw MCP connection hook (`uvx aegis run`) is injected globally.
- **Local**: Custom instructions (`"You are governed by the Aegis Microkernel..."`) are deployed locally via `CLAUDE.md`, `GEMINI.md`, and `AGENTS.md`. This prevents Aegis from enforcing rules on unrelated projects.

### Domains
1. **Policy Domain**: Translates `.aegis/rules/*.yaml` into models. 
2. **Evaluation Domain**: Dispatches analysis to specialized engines (Polyglot AST, Import Graph, Hardened Semantic).
3. **Coordination Domain**: Introduces the Cross-Agent Session Manager (`.aegis/session.json`) to facilitate technical handoffs between different AI agents.

---

## Agent Native Pattern
- No OS friction. No git hooks.
- Agents connect via MCP stdio (`uvx aegis run`).
- **Claude**: `CLAUDE.md` integration.
- **Gemini**: `GEMINI.md` integration.
- **Aider**: Self-healing loops via `--test-cmd: uvx aegis run --headless-check`.

## Consequences
- **Pros**: Zero workspace pollution, perfectly silent in ungoverned projects, deterministic structural evaluation, efficient context usage, coordinated multi-agent workflows.
- **Cons**: Requires one-time `aegis init` setup to write the global hooks.
