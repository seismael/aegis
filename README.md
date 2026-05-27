# Aegis V4 — Universal Agent-Native Architectural Microkernel

Aegis is an **Agent-Native Architectural Microkernel** that mathematically governs autonomous code generation. It lives inside Claude, Aider, and Gemini CLI via MCP to ensure your codebase stays clean, secure, and architecturally consistent.

---

## ⚡ Quick Start

```bash
pip install aegis
aegis install          # Injects Aegis into Claude, Aider, and Gemini
```

### 1. Initialize
Open your AI agent in any repository and type:
> `/aegis-init`

The agent will discover your architecture and scaffold appropriate governance rules.

### 2. Code Normally
Aegis is **invisible** until needed. Before the agent declares any task "done," it natively calls the Aegis compliance gate.

### 3. Self-Healing
If the agent introduces architectural drift, Aegis provides immediate remediation steps. The agent fixes the code **natively** before you ever see it.

---

## 🏗️ How It Works

Aegis is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server. Unlike traditional CI tools, Aegis runs **inside the agent's cognition loop**:

- **Universal Harnesses**: Seamlessly supports **Claude Code**, **Aider**, and **Gemini CLI**.
- **Re-entrant Semantics**: Forces agents to self-evaluate high-level design intents (e.g., "Domain logic must not leak into Controllers") using generated rubrics.
- **Incremental Graph**: High-performance $O(1)$ workspace-wide dependency analysis.
- **Cross-Agent Coordination**: Allows multiple agents to share validation state and handoff notes via `.aegis/session.json`.

---

## 🛠️ Tool Surface

| Tool | Purpose |
|------|---------|
| `validate_architecture_compliance` | **The Gate.** JIT compliance check before completion. |
| `request_semantic_grading_rubric` | **The Brain.** Re-entrant LLM self-grading for design intents. |
| `scaffold_governance_framework` | **The Setup.** Bootstrap rule packs and instruction files. |
| `plan_architecture` | **The Map.** Pre-emptive rule context before editing. |
| `query_knowledge_graph` | **The Introspection.** Dependency graphs and project health. |
| `evolve_ruleset` | **The Lifecycle.** Add rules, suppress debt, and manage packs. |

---

## 📦 Rule Packs

Aegis comes bundled with 18+ battle-tested rule packs:
- **Architecture**: DDD tactical patterns, layered boundaries, hexagonal isolation.
- **Security**: PII exposure, hardcoded secrets, input validation.
- **Performance**: N+1 queries, heavy loops, memory leaks.
- **Polyglot Support**: Python, TypeScript/JavaScript, and Rust.

---

## 🌐 Enterprise & Observability

- **Telemetry**: Local JSON check history in `.aegis/telemetry.json`.
- **OTLP Export**: Native support for Datadog, Grafana, and OpenTelemetry.
- **Custom Analyzers**: Plugin architecture for building your own structural engines.

---

## 📄 License

MIT License
