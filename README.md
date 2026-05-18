# Aegis: Universal AI Agentic Governance Protocol

**Aegis** is the definitive governance layer for autonomous AI coding. It enforces architectural compliance and prevents structural drift in **agentic workflows** via native agent integration (Claude, Aider, OpenDevin, Gemini) and real-time AST enforcement.

---

## 🚀 The Core Proposition: Active Enforcement

In AI-assisted engineering, agents often optimize for localized fixes while inadvertently violating global architectural principles. Aegis provides the missing "Governance Layer" for the agentic stack.

### Key Capabilities
- **Native Agentic Integration**: Seamlessly binds to AI tools via the **Model Context Protocol (MCP)**.
- **Hunk-Aware Gating**: Ultra-fast AST analysis that targets only modified lines, eliminating legacy noise.
- **RAG-Based Remediation**: Generates high-fidelity refactoring prompts with code context to prevent agent hallucination.
- **Multi-Engine Analysis**: Enforces laws via **Tree-sitter (AST)**, **Graph (Dependency)**, and **Regex** analyzers.

---

## 🛠️ Quick Start

### 1. Global Installation
Register Aegis globally into your agentic toolchain:

**Claude Code**:
```text
/plugin install https://github.com/aegis-governance/aegis
```

**Aider**:
```bash
aider --mcp-server "uv run aegis-kernel"
```

**Universal (Manual CLI)**:
```bash
uv run aegis install
```

### 2. Project Activation
Initialize governance for a specific repository:
```bash
aegis init
```

---

## 🏛️ Professional Governance
Aegis is designed for professional environments where architectural consistency is paramount.

| Capability | Enterprise Value |
|---|---|
| **Architectural Baselines** | Snapshot technical debt and enforce "no new drift" on legacy codebases. |
| **Self-Governance** | Aegis enforces its own OOD and Hexagonal laws on its own source code. |
| **Consensus Logging** | Every rule evolution is recorded with professional rationale in `evolution_log.json`. |
| **CI/CD Native** | Non-zero exit codes for blocking violations make it ideal for automated quality gates. |

---

## 🟢 Contribute
We are building the first universal governance engine for the agentic age. We actively seek contributions from **Software Architects**, **Security Engineers**, and **DevOps Specialists**.

Visit our [**Issue Tracker**](https://github.com/seismael/aegis/issues) to find curated tasks labeled by **role**, **domain**, and **ecosystem**. Look for the `good-first-issue` label to get started.

---

## ⚖️ License
Aegis is released under the **Apache License 2.0**, facilitating professional, enterprise, and community adoption.

**Govern your architecture. Empower your agents. Automate your perfection.**
