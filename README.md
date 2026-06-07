# Aegis V4 — Universal Agent-Native Architectural Microkernel

## 🤔 Why Aegis? What Does It Solve?

As AI coding agents (like Claude Code, Aider, and Gemini) become increasingly autonomous, they generate thousands of lines of code without deep awareness of your project's architectural constraints. This leads to:
- **Architectural Drift:** Agents silently violating Domain-Driven Design (DDD) boundaries, leaking presentation logic into domain models.
- **Security Vulnerabilities:** Hardcoded credentials or PII leaks slipping past rapid agent iterations.
- **Technical Debt:** Suboptimal performance patterns (e.g., N+1 queries) accumulating under the hood.

**Aegis solves this by acting as a mathematical microkernel that governs your agents.** It intercepts code generation in real-time via the Model Context Protocol (MCP), validates modifications against your bespoke architectural rules, and rejects non-compliant code *before* the agent finishes its task. Aegis forces AI to self-correct and adhere strictly to your established software design patterns.

---

## ⚡ Quick Start

```bash
pip install aegis
aegis init             # Initializes local workspace configuration for Claude, Aider, and Gemini
```

### 1. Initialize
Open your AI agent in any repository and type:
> `/aegis-init`

Aegis will **negotiate** your architecture. It discovers your frameworks (FastAPI, React, etc.) and proposes bespoke governance laws for your approval.

### 2. Ambient Awareness
Aegis is **invisible** until needed. As you navigate files, Aegis "whispers" architectural context to your agent via MCP resources, ensuring it knows the rules *before* it starts writing code.

### 3. Self-Healing
If an agent introduces architectural drift, Aegis provides a **Unified Diff**. Your agent can fix the code **natively and automatically** with a single tool call.

---

## 🏗️ Core Capabilities

- **Universal Harnesses**: Seamless, plugin-based support for **Claude Code**, **Aider**, and **Gemini CLI**.
- **Architect-on-Demand**: High-level conversational skills (`discover`, `apply`, `request_exception`) that replace complex YAML management.
- **Ambient Context**: JIT delivery of module-specific rules via `aegis://context/{path}`.
- **Re-entrant Semantics**: Mandatory rubrics for high-level design intents (e.g., "Domain logic must not leak into Controllers").
- **Incremental Graph**: High-performance $O(1)$ workspace-wide dependency analysis via JIT adjacency caching.
- **Cross-Agent Coordination**: Share validation state and handoff notes between different agents via `.aegis/session.json`.

## 🛠️ MCP Tools

Aegis provides a robust suite of Model Context Protocol (MCP) tools for your AI to autonomously manage architecture:

| Tool | Purpose |
|-------|---------|
| `check_architecture` | **The Gate.** JIT compliance check before completion (supports Diffs). |
| `find_patterns` | **The Scout.** Proactive pattern detection and law proposals. |
| `apply_rules` | **The Architect.** Formally adopts rule packs or custom intents. |
| `init_governance` | **The Bootstrapper.** Scaffolds `.aegis/` framework and native instructions. |
| `fetch_rubric` | **The Brain.** Re-entrant LLM self-grading for design intents. |
| `manage_rules` | **The Editor.** Evolve, add, or suppress active governance rules. |
| `query_graph` | **The Map.** $O(1)$ adjacency queries to understand module boundaries. |
| `get_scorecard` | **The Dashboard.** Updates the `.aegis/AEGIS.md` scorecard. |
| `plan_architecture` | **The Blueprint.** Plan cross-cutting structural modifications. |
| `request_exception` | **The Lawyer.** Petition for documented exceptions to specific laws. |

## 🤖 Chat Personas (Skills)

You can invoke specialized architectural personas directly in your chat:

| Skill | Persona |
|-------|---------|
| `/aegis-lead` | **Principal Architect.** Your primary persona for steering project architecture. |
| `/aegis-init` | **Bootstrapper.** Analyzes a new project and proposes baseline governance. |
| `/aegis-builder`| **Rule Author.** Translates plain English constraints into Aegis YAML rules. |
| `/aegis-grade` | **Semantic Auditor.** Enforces domain language and naming convention compliance. |

---

## 📦 Rule Packs

Aegis comes bundled with 18+ battle-tested rule packs:
- **Architecture**: DDD patterns, hexagonal isolation, layered boundaries.
- **Security**: PII detection, cloud-isolation, credential leak prevention.
- **Performance**: N+1 query detection, heavy loop analysis, memory leaks.
- **Polyglot**: Native AST support for Python, TypeScript, JavaScript, and Rust.

---

## 🌐 Enterprise & Observability

- **Scorecard (`.aegis/AEGIS.md`)**: A markdown dashboard for human and agent visibility.
- **Telemetry**: Local JSON check history in `.aegis/telemetry.json`.
- **OTLP Export**: Native support for Datadog, Grafana, and OpenTelemetry.

---

## 📄 License

MIT License
