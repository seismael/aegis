# Aegis Architectural Specification (v1.2)

## 1. Executive Vision
**Aegis** is an enterprise-grade, agentic architectural governance engine. It operates as a localized **Agentic Microkernel** that facilitates the negotiation, codification, and active enforcement of architectural consensus between human engineers and AI coding agents via the **Model Context Protocol (MCP)**.

---

## 2. The Agentic Governance Paradigm
Aegis distinguishes between **Authoring** (Negotiation) and **Enforcement** (Gating).

### 2.1 Skill-Based Authoring (External)
Architectural laws are discovered and codified via **AI Skills** (e.g., `.claude/skills/aegis-init.md`). This allows for context-aware, natural language negotiation of invariants that rigid terminal forms cannot achieve.
- **Output**: `.aegis/rules.yaml` (The Machine-Parseable Matrix).

### 2.2 Engine-Based Enforcement (Internal)
The Python core is a high-performance, stateless execution engine that consumes structured rules and applies them to the syntax tree of the project.

---

## 3. Core Subsystems

### 3.1 The Logical Constraint Matrix
The "Law" is stored in `.aegis/rules.yaml` as a collection of typed **Rule** models:
- **Logic**: Language-specific Tree-sitter S-expression queries.
- **Positive Enforcement**: `candidates_query` vs `check_query` for presence-based rules.
- **Enforcement Mode**: Escalates from `silent` to `block`.

### 3.2 The Technical Debt Oracle (Baseline)
Aegis supports **Brownfield Convergence** via structural signature hashing. LEGACY debt is grandfathered, while NEW drift is blocked at the source.

---

## 4. System Topology (Hexagonal)

### 4.1 Domain Layer
- **Policy Domain**: Structured YAML-to-Rule validation.
- **Evaluation Domain**: AST analysis, Baseline matching, and Workspace orchestration.
- **Enforcement Domain**: Remediation prompt synthesis.
- **Evolution Domain**: Consensus logging and decision persistence.

### 4.2 Infrastructure Layer
- **AST Engine**: Multi-parser Tree-sitter integration.
- **VCS Provider**: Hunk-aware Git diffing.
- **Persistence**: Local JSON/YAML storage.

### 4.3 Kernel Layer (Interface)
- **CLI Router**: Headless CI/CD gatekeeper (**`AegisCLI`**).
- **MCP Facade**: Stateless JSON-RPC server (**`AegisKernel`**).
- **Composition Root**: Unified **`Container`** for dependency injection.

---

## 5. System Invariants

1. **Local Isolation**: 100% local execution; no external dependencies.
2. **Stateless Logic**: The engine is reactive to the current `.aegis/` state.
3. **Self-Governance**: Aegis enforces its own OOD and isolation laws using its internal `check` engine.
