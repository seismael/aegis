# Aegis: Universal Architectural Governance Protocol

**Aegis** is a universal governance engine designed to automate architectural perfection. It transforms static design principles into **active execution gates**, ensuring structural compliance and preventing drift across any development workflow.

Aegis solves the problem of **architectural erosion** by introducing a high-performance, real-time feedback loop that enforces your project's core laws at the moment of code creation.

---

## 🎯 Core Objectives

- **Enforce Structural Invariants**: Mathematically verify that your code follows its intended design (e.g., Hexagonal boundaries, OOD principles).
- **Eliminate Architectural Drift**: Automatically detect and block "leaky" abstractions and paradigm violations before they enter your codebase.
- **Automate Quality Gates**: Provide instant, context-rich feedback to developers (and automated tools) to ensure every change adheres to the project's standards.
- **Manage Technical Debt**: Use sophisticated baselining to "grandfather" legacy violations while strictly enforcing zero-drift on new code.

---

## 🚀 Key Capabilities

- **Real-Time AST Enforcement**: Deep structural analysis using **Tree-sitter** that targets only modified code for ultra-fast feedback.
- **Polyglot Analysis**: Unified governance across multiple languages (Python, TypeScript, JavaScript, Rust).
- **Universal Integration**: Seamlessly binds to your existing toolchain via the **Model Context Protocol (MCP)** and standard CLI interfaces.
- **Modular Policy-as-Code**: Define your laws in simple YAML files organized by category (Architecture, Security, Style).
- **Extensible Plugin System**: Build custom analyzers for specialized domain needs using a robust platform interface.

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
