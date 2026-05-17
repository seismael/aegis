# Aegis: The Agentic Architectural Governance Engine

**Aegis** is an enterprise-grade, agentic architectural governance engine designed for the era of autonomous AI development. It solves the critical problem of **architectural drift** by enforcing structural invariants, Object-Oriented Design (OOD) paradigms, and Hexagonal boundaries through a high-performance, gated feedback loop.

---

## 🛠️ The Problem: Architectural Drift
In AI-assisted development, agents often optimize for localized fixes while inadvertently violating global architectural laws. This leads to:
- **Paradigm Leaks**: Procedural functions bleeding into strict OOD systems.
- **Dependency Rot**: Circular dependencies and domain-infrastructure coupling.
- **Technical Debt**: Unmanaged accumulation of structural violations.

## 🛡️ The Solution: Aegis Governance
Aegis provides a stateless, headless microkernel that facilitates negotiation and active enforcement of architectural consensus between humans and AI agents.

1. **Skill-Based Authoring**: AI agents use native skills to discover and codify your project's "Perfection" into a structured YAML matrix.
2. **Hunk-Aware Enforcement**: Aegis targets only modified lines via **Tree-sitter v0.25+**, ensuring zero-friction governance even on legacy brownfield projects.
3. **Consensus Evolution**: Architecture grows via a negotiated evolution loop, recording team rationale for every structural decision.
4. **Self-Governance**: Aegis is the first framework that uses its own engine to enforce its excellence.

---

## 🚀 Getting Started

### 1. Global Installation (Agent Level)
Install Aegis once per machine to register it as a native capability for Claude, Aider, and other tools.
```bash
pip install aegis-governance  # Or use uv
aegis install
```

### 2. Project Activation (Repository Level)
Initialize governance in your current repository. This creates the `.aegis/` environment and wires local Git pre-commit hooks.
```bash
aegis init
```

### 3. Negotiation (AI-Driven)
In your AI tool (e.g., Claude Code), run the initialization skill to codify your laws:
```text
/aegis-init
```

---

## 🛠️ Command Topology

| Command | Action |
|---|---|
| `aegis status` | Displays active rules, debt metrics, and evolution log. |
| `aegis check` | Gated verification (staged/CI) with non-zero exit codes. |
| `aegis baseline` | Snapshotting and managing technical debt (Grandfathering). |
| `aegis apply` | Displays diagnostic remediation prompts for AI agents. |
| `aegis evolve` | Initiates the consensus loop to modify project laws. |

---

## ⚖️ License
Aegis is released under the **GNU GPLv3** license, ensuring it remains a free, community-improving asset for all.

**Govern your architecture. Automate your excellence.**
