# Aegis: Agentic Operational Invariants

This document defines the **Governance Protocol** that AI agents must follow when operating within the Aegis ecosystem. These invariants ensure that architectural integrity is maintained through autonomous development cycles.

---

## 🏛️ Governance Protocol
- **MANDATORY**: Run `uv run aegis check` before every commit or when a logical feature task is complete. Blocking violations MUST be resolved or baselined.
- **TRANSPARENCY**: Run `uv run aegis status` to inspect the current rule matrix and debt ledger.
- **DEBT MANAGEMENT**: Baseline new or unavoidable violations with `uv run aegis baseline`. Never suppress violations silently.
- **RATIONALE**: Every rule modification must include a clear, professional rationale stored via the `aegis-rule-modify` skill.

---

## 🛠️ Development Workflow
- **Test-Driven Development (TDD)**: Always draft tests before feature logic. Run `uv run pytest tests/` after every code change.
- **Professional Formatting**: Run `ruff check --fix && ruff format` before every commit.
- **Architectural Isolation**: Adhere strictly to the **Hexagonal** pattern. Domain logic must never import from infrastructure adapters.
- **Language Awareness**: When authoring rules, prioritize the correct engine:
    - **AST (Tree-sitter)** for structural laws.
    - **Graph** for cross-module coupling.
    - **Regex** for simple pattern invariants.

---

## 🔌 MCP Interface (Agent Integration)

Agents should leverage the following MCP capabilities to ensure seamless governance:

### Core Tools
- `validate_architecture_compliance`: Perform a hunk-aware or full-workspace scan.
- `apply_architectural_remediation`: Receive structured fix instructions for violations.
- `get_rule_rationale`: Trace the history and "Why" of any law.
- `get_dependency_graph`: Inspect module coupling and identify leaks.

### Governance Resources
- `aegis://rules`: Inspect the full active rule matrix.
- `aegis://baseline`: Access the technical debt ledger.
- `aegis://evolution`: Review the auditable history of architectural decisions.

### Standardized Prompts
- `evaluate-architecture`: The primary compliance loop (Scan → Fix → Re-validate).
- `remediate-violations`: A guided workflow for fixing complex structural drift.

---

## 🛡️ Self-Governance
Aegis is a **Self-Governing Engine**. It enforces its own OOD, Hexagonal isolation, and documentation hygiene. The project MUST remain self-compliant with **zero active violations** at all times.

## 🧠 Agent Skills

### Issue Tracker
All work is tracked via GitHub Issues. AI agents should use the `gh` CLI to interact with the repository's task matrix.

### Triage Labels
We use a deterministic labeling system:
- `role:*` (Architect, Security, DevOps)
- `domain:*` (Governance, Compliance, Strategy)
- `ecosystem:*` (MCP, Tree-sitter)
- `intent:*` (Review, Expansion)
