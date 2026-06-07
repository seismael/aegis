# ADR 004: Cross-Agent Session State

## Status
Accepted

## Context
Aegis operates as a stateless Microkernel. It is booted up dynamically by whatever AI agent is currently active (e.g., Claude Code, Gemini). However, complex architectural implementations often span multiple sessions or even multiple different AI agents (e.g., using Gemini to plan an architecture, and Aider to implement it). Without a coordination mechanism, agents will overwrite each other's work or lose the context of *why* an architectural decision was made.

## Decision
We implemented the **Cross-Agent Session Manager**.

1. **State File**: The kernel maintains a local `.aegis/session.json` file.
2. **Handoffs**: When an agent performs a significant architectural analysis or creates a plan, the data is serialized into the session file.
3. **Resumption**: When a new agent (or the same agent later) boots up Aegis, the Kernel automatically loads the session file, allowing the new agent to read the active architectural context, pending proposals, and health state left behind by its predecessor.

## Consequences
- **Pros**: Enables true multi-agent collaboration. The repository itself becomes the source of truth, not the individual agent's isolated chat history. Preserves the stateless nature of the kernel relative to the OS.
- **Cons**: Adds a small IO overhead during agent initialization to read the session state. Requires agents to be explicitly instructed to read the session state.
