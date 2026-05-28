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

---

## 🛠️ Tool Surface (Skills)

| Skill | Purpose |
|-------|---------|
| `validate_architecture_compliance` | **The Gate.** JIT compliance check before completion (supports Diffs). |
| `discover_architectural_patterns` | **The Scout.** Proactive pattern detection and law proposals. |
| `apply_governance_law` | **The Architect.** Formally adopts rule packs or custom intents. |
| `request_exception` | **The Lawyer.** Petition for documented exceptions to specific laws. |
| `generate_health_scorecard` | **The Dashboard.** Updates the root-level `AEGIS.md` scorecard. |
| `request_semantic_grading_rubric` | **The Brain.** Re-entrant LLM self-grading for design intents. |

---

## 📦 Rule Packs

Aegis comes bundled with 18+ battle-tested rule packs:
- **Architecture**: DDD patterns, hexagonal isolation, layered boundaries.
- **Security**: PII detection, cloud-isolation, credential leak prevention.
- **Performance**: N+1 query detection, heavy loop analysis, memory leaks.
- **Polyglot**: Native AST support for Python, TypeScript, JavaScript, and Rust.

---

## 🌐 Enterprise & Observability

- **Scorecard (`AEGIS.md`)**: A root-level Markdown dashboard for human and agent visibility.
- **Telemetry**: Local JSON check history in `.aegis/telemetry.json`.
- **OTLP Export**: Native support for Datadog, Grafana, and OpenTelemetry.

---

## 📄 License

MIT License
