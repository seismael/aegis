# Aegis: The Universal Agentic Governance Capability

**Aegis** is an enterprise-grade architectural governance engine that installs as a **native extension** into your AI coding agents (Claude, Aider, OpenCode, etc.). It transforms architecture from a static document into an **active execution gate**, solving the problem of architectural drift in autonomous development.

---

## 🛡️ The Problem: Architectural Drift
AI agents often optimize for localized fixes while inadvertently violating global architectural laws. Aegis solves this by introducing a stateless, high-performance feedback loop that enforces your project's "Perfection" at the moment of code creation.

## 🚀 Native Agentic Integration (The "Universal" Paradigm)
Aegis is not a traditional global OS tool; it is a **Universal Capability** that you install once into your agentic ecosystems:

### 1. Global Installation (Agent Level)
Register Aegis as a native skill and MCP capability in your primary AI tools.
```bash
# Installs Aegis globally into Claude, Aider, and other agent toolchains
uv run aegis install
```
*Impact: Your AI agents now natively "know" how to discover, evaluate, and remediate architecture.*

### 2. Project Activation (Repository Level)
Enable the governance protocol for a specific repository.
```bash
# Bootstraps the .aegis/ law-matrix for the current project
aegis init
```

### 3. Agentic Workflow (Universal)
Once initialized, any agent entering the repository is governed by the **Aegis Protocol** (documented in `AGENTS.md`).
- **Claude**: Use `/aegis-init` to negotiate your laws.
- **Aider**: The engine is automatically mapped as an architect-mode MCP server.
- **All Agents**: Use `validate_architecture_compliance` to ensure perfection before every commit.

---

## 🛠️ Command Ecosystem

| Capability | Command | Role |
|---|---|---|
| **Installer** | `aegis install` | **Universal Plugin Bootstrapper**: Wires Aegis into all agent tools globally. |
| **Gating** | `aegis check` | **Headless Gatekeeper**: Enforces laws in CI/CD and pre-commit hooks. |
| **Audit** | `aegis status` | **Governance Dashboard**: Summarizes rules, debt, and evolution logic. |
| **Consensus** | `aegis evolve` | **Negotiation Bridge**: Interactive loop for rule evolution and debt suppression. |

---

## ✅ Why Aegis?
-   **Agnostic**: One protocol for Claude, Aider, Gemini, and future agents.
-   **Hunk-Aware**: Ultra-fast analysis that targets only your current changes.
-   **Self-Governing**: The only framework that enforces its own architectural excellence.
-   **Copyleft (GPLv3)**: A community-owned standard for the future of software excellence.

**Govern your architecture. Empower your agents. Automate your perfection.**
