# Aegis: Technical Target Specification

## Layer 0: The Universal Bootstrapper
Aegis provides a global installation layer that binds into the developer's agentic toolchain.
- **Universal Command**: `uv run aegis install`
- **Action**: Registers the Aegis MCP server into global configurations (e.g., `claude_desktop_config.json`, `.aider.conf.yml`) and deploys agentic skills to native skill directories.
- **Invariant**: The installer is idempotent and project-agnostic.

## Layer 1: The Governance Microkernel
The Aegis Kernel is the engine of **Architectural Enforcement**. It supports three primary evaluation strategies:
1.  **AST (Tree-sitter)**: Language-aware structural analysis.
2.  **Graph**: Cross-file dependency and coupling analysis.
3.  **Regex**: High-speed pattern matching for simple invariants.

## Layer 2: Domain Architecture (Execution Engine)
- **Policy Domain**: Orchestrates the YAML-to-Model transformation. Supports multi-engine routing and scope-aware filtering.
- **Evaluation Domain**: Dispatches analysis to the specialized engines. Implements hunk-aware diffing to ensure performance.
- **Enforcement Domain**: Decision engine for gating (allow/warn/block) and remediation synthesis.
- **Evolution Domain**: Persistent ledger of consensus decisions (`evolution_log.json`) and technical debt (`baseline.json`).

## Layer 3: The Agentic Interface (MCP)
The **Aegis Kernel** exposes its capabilities via the **Model Context Protocol (MCP)**, offering three tiers of integration:

### 3.1 Tools (Actionable Commands)
- `validate_architecture_compliance`: Executes a full-workspace or hunk-aware scan.
- `apply_architectural_remediation`: Returns structured, RAG-optimized fix instructions.
- `get_rule_rationale`: Fetches the human-provided "Why" behind a law.
- `get_dependency_graph`: Visualizes module coupling and identifies leaks.

### 3.2 Resources (Governance Artifacts)
- `aegis://rules`: The machine-readable rule matrix.
- `aegis://baseline`: The technical debt ledger.
- `aegis://evolution`: The auditable decision log.

### 3.3 Prompts (Workflow Templates)
- `evaluate-architecture`: A standard workflow for agents to verify compliance before submission.
- `remediate-violations`: A guided workflow for fixing complex architectural drift.

## Layer 4: Active Law Matrix
Current active rules are defined in `.aegis/rules/*.yaml`. For the latest state of the project's self-governance, refer to the rule matrix via `aegis status`.
