# Aegis: The Agentic Architectural Governance Engine

**Aegis** is an enterprise-grade framework for **Negotiated Architectural Governance**. It provides the infrastructure to codify and programmatically enforce architectural invariants across any codebase, regardless of language or paradigm.

By treating architecture as an **active execution gate**, Aegis bridges the gap between high-level human intent and autonomous AI development cycles.

## 🧠 The Aegis Workflow

### 1. Bootstrap (`aegis init`)
Initialize the project environment. Aegis creates a `.aegis/` directory to store your project's architectural laws and state.

### 2. Negotiate (AI Skill-Based)
Use the **`/aegis-init`** skill in your AI agent (Claude Code, etc.) to discover and codify your project's perfection. The skill generates a structured `.aegis/rules.yaml` matrix tailored to your repo.

### 3. Enforce (`aegis check --staged`)
Aegis intercepts your development loop. Use the gated check command in pre-commit hooks to block any structural drift before it reaches your repository.

### 4. Converge (`aegis baseline`)
Adopt Aegis on brownfield projects without the noise. "Grandfather" existing violations into a baseline ledger, ensuring you only ever improve or stay stable.

### 5. Evolve (`aegis evolve`)
Architecture isn't static. Negotiate rule relaxation or suppress specific violations through a consensus loop that records decision rationale for the whole team.

## 🚀 Core Capabilities

- **Structured Matrix**: Rules are stored as versionable YAML with per-rule enforcement modes.
- **Hunk-Aware Analysis**: Only checks modified lines, ensuring high performance and low noise.
- **Positive Enforcement**: Supports "X must have Y" rules via candidate-complement checking.
- **Agentic Integration**: Natively interfaces with frontier AI tools via the Model Context Protocol (MCP).

## 🛠️ Usage

```bash
# Setup
uv run aegis init
uv run aegis setup-hooks

# Audit
uv run aegis status
uv run aegis evaluate

# Enforcement (Gated)
uv run aegis check --staged
```
