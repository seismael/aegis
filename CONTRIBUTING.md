# Contributing to Aegis

Welcome to the Aegis community! We are building the first universal governance engine for the agentic age. Whether you are a software architect, a security specialist, or a passionate engineer, your contributions are vital to our mission of automating architectural perfection.

---

## 🟢 How to Get Started

We value specialized professional perspectives.

### 1. Identify an Issue
- Browse our [Issue Tracker](https://github.com/seismael/aegis/issues).
- Look for the `good-first-issue` label.
- Filter by your expertise using our deterministic labels:
    - **Roles**: `role:architect`, `role:security-engineer`, `role:devops-sre`
    - **Domains**: `domain:agentic-governance`, `domain:security-compliance`
    - **Ecosystems**: `ecosystem:mcp-protocol`, `ecosystem:tree-sitter-ast`
- If you have a new idea, please open a **Discussion** first to align on the architectural direction.

### 2. Development Environment
Aegis uses `uv` for modern Python package management.
```bash
# Clone the repository
git clone https://github.com/aegis-governance/aegis.git
cd aegis

# Synchronize dependencies
uv sync

# Install the Aegis MCP server globally for local testing
uv run aegis install
```

---

## 🏛️ The "Self-Governance" Protocol
Aegis is a self-referential system. We use the engine to enforce the project's own architectural invariants. **Your PR cannot be merged if it violates these laws.**

1.  **Strict OOD**: Encapsulate logic in domain services and models.
2.  **Hexagonal Isolation**: Domain logic must never import from the infrastructure layer.
3.  **TDD First**: Every feature or fix must be accompanied by comprehensive tests.
4.  **Verification**: Run the full suite before submitting:
    ```bash
    uv run pytest tests/
    uv run aegis check  # The ultimate gate
    ```

---

## ⚖️ License & Attribution
By contributing to Aegis, you agree that your contributions will be licensed under the **Apache License 2.0**. We strive for a professional environment where all contributors are respected and recognized.

**Thank you for helping us govern the future of autonomous engineering.**
