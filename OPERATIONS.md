# Aegis: Operational Invariants

This document defines the **Governance Protocol** that ensures architectural integrity is maintained through every development cycle. These invariants apply to all contributors and automated tools operating within the Aegis ecosystem.

---

## 🏛️ Governance Protocol
- **MANDATORY**: Run `uv run aegis check` before every commit or when a logical task is complete. Blocking violations MUST be resolved or baselined.
- **TRANSPARENCY**: Run `uv run aegis status` to inspect the current rule matrix and debt ledger.
- **DEBT MANAGEMENT**: Baseline new or unavoidable violations with `uv run aegis baseline`. Never suppress violations silently.
- **RATIONALE**: Every rule modification must include a clear rationale stored via the evolution protocol.

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

Aegis leverages the **Model Context Protocol (MCP)** to provide seamless integration with development tools:

### Core Tools
- `validate_architecture_compliance`: Perform a hunk-aware or workspace scan.
- `apply_architectural_remediation`: Receive structured fix instructions for violations.
- `get_rule_rationale`: Trace the history and reasoning behind any law.
- `get_dependency_graph`: Inspect module coupling and identify leaks.

### Governance Resources
- `aegis://rules`: Inspect the full active rule matrix.
- `aegis://baseline`: Access the technical debt ledger.
- `aegis://evolution`: Review the auditable history of architectural decisions.

---

## 🛡️ Self-Governance
Aegis is a **Self-Governing Engine**. It enforces its own structural invariants, isolation, and documentation hygiene. The project MUST remain self-compliant with **zero active violations** at all times.

## 🧠 Environment Capabilities

### Issue Tracker
All work is tracked via GitHub Issues. Use the `gh` CLI to interact with the repository's task matrix.

### Triage Labels
We use a deterministic labeling system:
- `role:*` (Architect, Security, DevOps)
- `domain:*` (Governance, Compliance, Strategy)
- `ecosystem:*` (MCP, Tree-sitter)
- `intent:*` (Review, Expansion)
