# Contributing to Aegis

We love your input! We want to make contributing to Aegis as easy and transparent as possible, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features
- Becoming a maintainer

## Our Development Process

Aegis is a self-governing project. All contributions must pass the `aegis check` enforcement gate before they can be merged.

1. **Fork the repo** and create your branch from `main`.
2. **Setup environment**: Use `uv sync` to install dependencies and `uv run aegis setup-hooks` to install pre-commit hooks.
3. **Make your changes**: If you add new functionality, please include tests.
4. **Self-Governance Audit**: Run `uv run aegis self-check` to ensure your changes comply with the project's own architectural invariants.
5. **Issue a PR**: Link any related issues in your description.

## Architectural Standards

Aegis follows a **Hexagonal / Microkernel Architecture**.
- **Domain Layer**: Must be pure Python and isolated from infrastructure.
- **Strict OOD**: All core logic should be encapsulated in classes/services.
- **Tree-sitter Queries**: Ensure queries are optimized and language-agnostic where possible.

## Any questions?

Feel free to open an issue or start a discussion!
