# Aegis: Universal Architectural Governance Protocol

**Aegis** is a universal governance engine designed to automate architectural perfection. It transforms static design principles into **active execution gates**, ensuring structural compliance and preventing drift across any development workflow.

Unlike traditional linters, Aegis is a **Steering-First** protocol. It provides proactive architectural guidance *before* code is written, ensuring that both human developers and autonomous agents remain aligned with project invariants by design.

---

## 🎯 Core Objectives

- **Proactive Architectural Steering**: Generate "Architectural Flight Plans" at the start of every task to align implementation with project goals.
- **Enforce Structural Invariants**: Mathematically verify that your code follows its intended design (e.g., Hexagonal boundaries, OOD principles).
- **Eliminate Architectural Drift**: Automatically detect and block "leaky" abstractions and paradigm violations in real-time.
- **Manage Technical Debt**: Use sophisticated structural baselining to "grandfather" legacy violations while strictly enforcing zero-drift on new code.

---

## 🚀 Key Capabilities

- **Steering-First Discovery**: Pre-fetch relevant architectural laws for any file path *before* editing.
- **Real-Time AST Enforcement**: Deep structural analysis using **Tree-sitter** that targets modified code for ultra-fast feedback.
- **Universal Integration**: Seamlessly binds to your toolchain via the **Model Context Protocol (MCP)** and standard CLI.
- **Modular Policy-as-Code**: Define laws in simple YAML files organized by category (Architecture, Security, Style).
- **Extensible Plugin Platform**: Build project-wide analyzers for specialized domain needs (e.g., dead code detection, cloud-isolation).

---

## 🛠️ Getting Started

### 1. Global Setup
Register Aegis into your local development environment:

```bash
# Register the Aegis protocol globally
uv run aegis install
```

### 2. Project Activation
Initialize governance for a specific repository:

```bash
# Bootstrap the .aegis/ law-matrix
aegis init
```

---

## 🏛️ Target Use Cases

| Use Case | Solution |
|---|---|
| **Layer Isolation** | Enforce strict boundaries between Domain, Application, and Infrastructure layers. |
| **Cloud-Native Decoupling** | Prevent cloud-provider SDKs from leaking into business logic. |
| **API Deprecation** | Manage migrations by blocking new usages of deprecated patterns while permitting existing ones. |
| **Security Invariants** | Detect hardcoded secrets and unsafe coding patterns in real-time. |
| **Modular Encapsulation** | Restrict access to private internal modules to authorized consumers only. |

---

## 🟢 Contribute
We welcome all developers who are passionate about architectural integrity.

Visit our [**Issue Tracker**](https://github.com/seismael/aegis/issues) to find curated tasks labeled by **role**, **domain**, and **intent**.

---

## ⚖️ License
Aegis is released under the **Apache License 2.0**, facilitating universal adoption and contribution.

**Govern your architecture. Automate your perfection.**
