# Aegis Architectural Specification (v1.3)

## 1. Executive Vision
**Aegis** is an enterprise-grade, agentic architectural governance engine. It operates as a localized **Agentic Microkernel** that facilitates the negotiation, codification, and active enforcement of architectural consensus between human engineers and AI coding agents via the **Model Context Protocol (MCP)**.

---

## 2. The Tiered Governance Paradigm
Aegis distinguishes between **Global Capability** (The Plugin) and **Local Governance** (The Law).

### 2.1 Global Agent Capability (The Installer)
Aegis acts as a native extension for AI agents. The **`aegis-install`** bootstrapper registers the engine globally in the user's AI toolchains (Claude, Aider, etc.). 
- **Impact**: AI agents carry the "Aegis Capability" into every project they enter.

### 2.2 Project-Level Governance (The Engine)
Once an agent enters a repository, they activate the local protocol via **`aegis init`**. The Python core then enforces the structured laws defined in that project's `.aegis/rules.yaml`.

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
- **Policy Domain**: Structured YAML-to-Rule validation and inheritance.
- **Evaluation Domain**: AST analysis, Baseline matching, and Workspace orchestration.
- **Enforcement Domain**: Remediation prompt synthesis (RAG-based).
- **Evolution Domain**: Consensus logging and decision persistence.

### 4.2 Infrastructure Layer (Adapters)
- **Agent Tool Adapters**: Native tool-specific integration logic (Claude, Aider).
- **AST Engine**: Multi-parser Tree-sitter integration.
- **VCS Provider**: Hunk-aware Git diffing.

### 4.3 Kernel Layer (Interface)
- **CLI Router**: Headless CI/CD gatekeeper and bootstrapper (**`AegisCLI`**).
- **MCP Facade**: Stateless JSON-RPC server with project management tools (**`AegisKernel`**).
- **Composition Root**: Unified **`Container`** for shared dependency injection.

---

## 5. System Invariants

1. **Local Isolation**: 100% local execution; no external telemetry.
2. **Stateless Enforcement**: The engine is reactive to the current `.aegis/` state.
3. **Self-Governance**: Aegis enforces its own OOD and isolation laws using its internal `check` engine.
