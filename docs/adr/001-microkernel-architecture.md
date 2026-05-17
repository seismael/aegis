# ADR 001: Agentic Microkernel Architecture

## Status
Proposed

## Context
Aegis needs to be a language-agnostic, extensible governance engine that can interface with multiple AI coding agents (Claude, Aider, etc.) via the Model Context Protocol (MCP).

## Decision
We will adopt a **Microkernel Architecture** (also known as Plug-in Architecture).
- **Core (Microkernel)**: Handles orchestration, state management, and the MCP server facade.
- **Subsystems (Plug-ins)**: Implement specific logic like AST analysis (Tree-sitter), Policy parsing (Markdown), and Debt tracking (JSON).
- **Infrastructure**: Handles external concerns like Git integration and File System access via the Repository pattern.

## Consequences
- **Pros**: High modularity, ease of adding new language support or analysis rules, clean separation of concerns.
- **Cons**: Slightly higher initial complexity in establishing the registration and orchestration logic.
