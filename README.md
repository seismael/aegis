# Aegis: The Universal Agentic Governance Capability

**Aegis** is an enterprise-grade architectural governance engine that installs as a **native extension** into your AI coding agents (Claude, Aider, OpenCode, etc.). It transforms architecture from a static document into an **active execution gate**, solving the critical problem of **architectural drift** in autonomous AI development.

---

## 🛠️ The Problem: Architectural Drift
In AI-assisted engineering, agents often optimize for localized fixes while inadvertently violating global architectural laws. This leads to paradigm leaks, dependency rot, and unmanaged technical debt. Aegis solves this by introducing a stateless, high-performance feedback loop that enforces your project's "Perfection" at the moment of code creation.

---

## 🚀 Native Agentic Integration (The "Universal" Paradigm)
Aegis is a **Universal Capability** that you install once into your agentic ecosystems using their native commands:

### 1. Global Installation (Native Tool Flow)
Install Aegis directly from GitHub into your preferred agent.

**Claude Code**:
```text
/plugin install https://github.com/seismael/aegis
```

**Aider**:
```bash
aider --mcp-server "uv run aegis-kernel"
```

**Universal (Manual CLI)**:
```bash
# Register Aegis globally into all detected tools on this machine
uv run aegis install
```
*Impact: Your AI agents now natively "know" how to discover, evaluate, and remediate architecture across any project.*

### 2. Project Activation (Repository Level)
Activate the governance protocol for a specific repository.
```bash
# Bootstraps the .aegis/ law-matrix and wires optional Git hooks
aegis init
```

### 3. Agentic Workflow (Universal)
Once initialized, any agent entering the repo follows the **Aegis Protocol**:
- **Claude**: Use `/aegis-init` to negotiate and codify your bespoke laws.
- **Aider**: The engine is automatically mapped as an architect-mode MCP server.
- **All Agents**: Use `validate_architecture_compliance` to ensure structural perfection before every commit.

---

## 🛠️ Core Capabilities

| Capability | Role |
|---|---|
| **Native Skills** | AI agents use built-in skills to discover, update, and evolve laws via natural language. |
| **Hunk-Aware Gating** | Ultra-fast AST analysis that targets only modified lines, eliminating legacy noise. |
| **RAG-Based Refactoring** | Generates high-fidelity remediation prompts with code context to prevent agent hallucination. |
| **Self-Governance** | The only framework that uses its own engine to enforce its internal OOD and Hexagonal laws. |

---

## 🛠️ CLI Command Ecosystem

| Command | Action |
|---|---|
| `aegis status` | Displays active rules, debt metrics, and evolution log. |
| `aegis check` | Gated verification (staged/CI) with non-zero exit codes. |
| `aegis baseline` | Snapshotting and managing technical debt (Grandfathering). |
| `aegis evolve` | Records consensus decisions to modify architectural laws. |

---

## ⚖️ License
Aegis is released under the **GNU GPLv3** license, ensuring it remains a shared, community-improving asset.

**Govern your architecture. Empower your agents. Automate your perfection.**
