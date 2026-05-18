# Aegis: Architectural Specification (v1.5)

## 1. Executive Vision
**Aegis** is an enterprise-grade architectural governance engine designed for the **Agentic Era**. It operates as a localized **Agentic Microkernel** that facilitates the negotiation, codification, and active enforcement of architectural consensus between human engineers and AI coding agents via the **Model Context Protocol (MCP)**.

---

## 2. The Tiered Governance Paradigm
Aegis distinguishes between **Global Capability** (the toolchain extension) and **Local Governance** (the repository-specific laws).

### 2.1 Global Agent Capability
Aegis acts as a native extension for AI agents. Through the `aegis-install` process, the engine is registered globally in the user's AI toolchain (Claude Desktop, Aider, etc.).
- **Strategic Impact**: AI agents carry the "Aegis Capability" into every project they enter, allowing them to instantly discover and respect local architectural boundaries.

### 2.2 Project-Level Governance
Upon entering a repository, an agent activates the local protocol via `aegis init`. The engine then enforces the structured laws defined in `.aegis/rules/`.

---

## 3. Core Subsystems

### 3.1 The Logical Constraint Matrix
Laws are stored as structured **Rule** models in YAML. Each rule defines:
- **Engine Type**: AST (Tree-sitter), Graph (Dependency), or Regex (Pattern).
- **Scope**: Inclusion and exclusion patterns (glob-based).
- **Severity**: Ranging from `report` (informational) to `block` (preventing commits).

### 3.2 The Technical Debt Oracle (Baseline)
Aegis enables **Brownfield Convergence** via structural signature hashing. Legacy violations are "grandfathered" into a `baseline.json` ledger, allowing the engine to block *new* architectural drift without requiring an immediate, massive refactor of existing code.

---

## 4. System Topology (Hexagonal)

Aegis follows a strict **Hexagonal Architecture** to ensure the core governance logic remains decoupled from specific AI agent adapters or file system implementations.

### 4.1 Domain Layer (Core)
- **Policy Domain**: Rule parsing, validation, and inheritance logic.
- **Evaluation Domain**: Orchestrates the analysis engines and manages technical debt baselines.
- **Enforcement Domain**: Synthesizes RAG-ready remediation prompts based on violations.
- **Evolution Domain**: Manages the auditable history of architectural decisions.

### 4.2 Infrastructure Layer (Adapters)
- **AST Engine**: Specialized Tree-sitter integration for multi-language support.
- **Graph Engine**: Analyzes module coupling and detects circular dependencies.
- **VCS Provider**: Provides hunk-aware diffing to ensure analysis is targeted and fast.

### 4.3 Kernel Layer (Interface)
- **MCP Facade**: The stateless JSON-RPC interface through which AI agents interact with the engine.
- **CLI Router**: The primary interface for CI/CD pipelines and manual developer interaction.

---

## 5. System Invariants

1. **Zero-Telemetry Privacy**: 100% local execution; no code or metadata ever leaves the local environment.
2. **Stateless Enforcement**: The engine is entirely reactive to the current `.aegis/` state and the local file system.
3. **Self-Governance**: Aegis enforces its own OOD and isolation laws using its internal checking engine.
