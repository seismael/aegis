# ADR 003: Universal Harness Abstraction

## Status
Accepted

## Context
Aegis is designed to govern AI agents, but there are multiple popular agent CLIs (Claude Code, Aider, Gemini CLI, Cursor, etc.). Tying Aegis to the internal execution model of a single agent would severely limit its adoption and shelf-life. We needed a way to inject Aegis's governance directives and MCP server connection into any agent seamlessly.

## Decision
We designed the **Universal Harness Abstraction** (`BaseHarness`):

1. **Agnostic Interface**: The `BaseHarness` defines a strict contract (`install_local`, `deploy_workspace_instructions`) that all specific harnesses must implement.
2. **CLI-Specific Implementations**:
   - `ClaudeHarness`: Manipulates `~/.claude.json` and `CLAUDE.md`.
   - `GeminiHarness`: Manipulates `~/.gemini.json` and `GEMINI.md`.
   - `AiderHarness`: Manipulates `~/.aider.conf.yml` and `AGENTS.md`.
3. **Safe Injection**: Harnesses use a shared `safe_append_instruction` utility to safely inject the `AEGIS_GOVERNANCE_DIRECTIVE` into local markdown files without overwriting or destroying existing user configurations.

## Consequences
- **Pros**: Aegis is completely agent-agnostic. Adding support for a new AI CLI takes minutes by subclassing `BaseHarness`.
- **Cons**: We must maintain compatibility with the configuration file formats of third-party tools, which may change over time.
