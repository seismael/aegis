# Aegis: Operational Invariants

This document defines the **Governance Protocol** that ensures architectural integrity is maintained through every development cycle. These invariants apply to all contributors and automated tools operating within the Aegis ecosystem.

---

## 🏛️ Governance Protocol: Steering-First

Aegis enforces a **Steering-First** methodology. You are mandated to use the following proactive cycle:

### 1. Discovery (Task Start)
- **MANDATORY**: Whenever starting a new logical task, call the `propose_architectural_steering` tool.
- Align your implementation strategy with the resulting **Architectural Flight Plan**.

### 2. Awareness (File Edit)
- **MANDATORY**: Before editing any specific file, call `get_relevant_rules(path)`.
- Explicitly respect the returned structural laws during generation.

### 3. Validation (Commit/Gate)
- **MANDATORY**: Run `uv run aegis check` before every commit.
- **TRANSPARENCY**: Run `uv run aegis status` to inspect the current rule matrix and debt ledger.
- **DEBT MANAGEMENT**: Baseline new or unavoidable violations with `uv run aegis baseline`. Never suppress violations silently.

---

## 🛠️ Development Workflow
- **Test-Driven Development (TDD)**: Always draft tests before feature logic. Run `uv run pytest tests/` after every code change.
- **Automated Formatting**: Run `ruff check --fix && ruff format` before every commit.
- **Architectural Isolation**: Adhere strictly to the **Hexagonal** pattern. Domain logic must never import from infrastructure adapters.
- **Engine Awareness**: When authoring rules, prioritize the correct engine:
    - **AST (Tree-sitter)** for structural laws.
    - **Graph** for cross-module coupling.
    - **Regex** for simple pattern invariants.

---

## 🔌 Integration Interface (MCP)

Aegis leverages the **Model Context Protocol (MCP)** to provide an intent-driven interface for development tools:

### Core Meta-Tools (V2.0)
- `plan_architecture`: Innovation — Task alignment and proactive rule discovery. Call this **FIRST**.
- `validate_workspace`: Comprehensive compliance gate and remediation engine.
- `evolve_ruleset`: Manage architectural laws, rule packs, and technical debt.
- `query_knowledge_graph`: Introspect project health, rationales, and dependencies.

### Governance Resources (Subscribe for Ambient Context)
- `aegis://context/{path}`: Ambient Architectural Context for a specific file. **SUBSCRIBE** to this resource for real-time steering.
- `aegis://rules`: Inspect the full active rule matrix.
- `aegis://baseline`: Access the technical debt ledger.
- `aegis://evolution`: Review the auditable history of architectural decisions.

---

## 🛡️ Self-Governance
Aegis is a **Self-Governing Engine**. It enforces its own structural invariants, isolation, and documentation hygiene. The project MUST remain self-compliant with **zero active violations** at all times.

## 🧠 Environment Capabilities

### The Principal Architect Persona
Use the `aegis-principal-architect` skill for all architectural alignment. This persona is your primary guide for maintaining project perfection.

### Issue Tracker
All work is tracked via GitHub Issues. Use the `gh` CLI to interact with the repository's task matrix.
