# Aegis Architectural Specification (v1.2)

## 1. Executive Vision
**Aegis** is an enterprise-grade, agentic architectural governance engine. It operates as a localized **Agentic Microkernel** that facilitates the negotiation, codification, and active enforcement of architectural consensus between human engineers and AI coding agents via the **Model Context Protocol (MCP)**.

---

## 2. The Agentic Governance Paradigm
Aegis distinguishes between **Authoring** (Negotiation) and **Enforcement** (Gating).

### 2.1 Skill-Based Authoring (External)
Architectural laws are discovered and codified via **AI Skills** (e.g., `.claude/skills/aegis-init.md`). This allows for context-aware, natural language negotiation of invariants that Python-based forms cannot achieve.
- **Output**: `.aegis/rules.yaml` (The Source of Truth).

### 2.2 Engine-Based Enforcement (Internal)
The Python core is a high-performance, stateless execution engine that consumes structured rules and applies them to the syntax tree of the project.

---

## 3. Core Archetypes & The Governance Matrix

### 3.1 The Logical Constraint Matrix
The "Law" is stored in `.aegis/rules.yaml` as a collection of typed **Rule** models:
- **Identity**: Unique ID, human-readable description.
- **Logic**: Language-specific Tree-sitter S-expression queries.
- **Positive Enforcement**: `candidates_query` vs `check_query` for presence-based rules.
- **Mode**: Enforcement level (`silent`, `report`, `warn`, `block`, `fix`).

### 3.2 The Technical Debt Oracle (Baseline)
Aegis supports **Brownfield Convergence** via a `.aegis/baseline.json` ledger.
- **Zero-Drift**: New violations are blocked, while legacy debt is grandfathered.

---

## 4. Governance Lifecycle & Command Topology

| Phase | Command | Responsibility |
|---|---|---|
| **Bootstrap** | `aegis init` | Initializes the `.aegis/` environment for AI skills. |
| **Audit** | `aegis evaluate` | Full-workspace sweep for architectural awareness. |
| **Dashboard** | `aegis status` | Displays active rules, debt metrics, and evolution log. |
| **Enforcement**| `aegis check` | Gated verification (staged/CI) with non-zero exit codes. |
| **Convergence**| `aegis baseline` | Snapshotting and managing technical debt. |
| **Remediation** | `aegis apply` | Automated refactoring via AI Agents or AST transforms. |
| **Evolution** | `aegis evolve` | Negotiated violation suppression and consensus recording. |

---

## 5. System Topology (Hexagonal)

### 5.1 Domain Layer (Pure Logic)
- **Policy Domain**: Structured YAML-to-Rule parsing and validation.
- **Evaluation Domain**: AST analysis, Baseline matching, and Workspace orchestration.
- **Enforcement Domain**: Remediation planning and strategy execution.
- **Evolution Domain**: Consensus logging and decision persistence.

### 5.2 Infrastructure Layer (Adapters)
- **AST Engine**: Tree-sitter (Multi-parser: Python, TS, etc.).
- **VCS Provider**: Git (Hunk-aware, line-level diffing).
- **Persistence**: File-system JSON/YAML storage.

### 5.3 Kernel Layer (Interface)
- **CLI Router**: User interface for human engineers.
- **MCP Facade**: JSON-RPC interface for AI agents.
- **Composition Root**: Unified `Container` for shared dependency injection.

---

## 6. System Invariants

1. **Isolation**: Entirely local execution; no external telemetry.
2. **Stateless Logic**: The engine does not maintain session state; it reacts to the current `.aegis/` filesystem state.
3. **Self-Governance**: Aegis enforces its own hexagonal boundaries using its internal `check` engine.
