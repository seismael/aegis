## V4 Agent-Native Invariants

### Mandatory Compliance Check

Before declaring ANY coding task complete, the AI agent MUST:

1. Call `validate_architecture_compliance` with the list of modified files.
2. If violations are returned, remediate the code natively.
3. Re-run validation until SUCCESS is returned.

### No Direct File System Governance

Aegis V4 never:
- Installs git hooks
- Watches file system events
- Intercepts file reads/writes
- Maintains session state

# Aegis: Technical Target Specification

## Layer 0: The Universal Bootstrapper
Aegis provides a global installation layer that binds into your development toolchain.
- **Universal Command**: `uv run aegis install`
- **Action**: Registers the Aegis MCP server into global configurations and deploys operational skills to native directories.
- **Invariant**: The installer is idempotent and project-agnostic.

## Layer 1: The Governance Microkernel
The Aegis Kernel is the engine of **Structural Enforcement**. It supports three primary evaluation strategies:
1.  **AST (Tree-sitter)**: Language-aware structural analysis.
2.  **Graph**: Cross-file dependency and coupling analysis.
3.  **Regex**: High-speed pattern matching for simple invariants.

## Layer 2: Domain Architecture (Execution Engine)
- **Policy Domain**: Orchestrates the YAML-to-Model transformation. Supports multi-engine routing and scope-aware filtering.
- **Evaluation Domain**: Dispatches analysis to specialized engines. Implements hunk-aware diffing to ensure performance.
- **Enforcement Domain**: Decision engine for gating (allow/warn/block) and remediation synthesis.
- **Evolution Domain**: Persistent ledger of decisions (`evolution_log.json`) and technical debt (`baseline.json`).

## Layer 3: The Integration Interface (MCP)
The **Aegis Kernel** exposes its capabilities via the **Model Context Protocol (MCP)**, offering three tiers of integration:

### 3.1 Tools (Actionable Commands)
- `propose_architectural_steering`: Innovation — Generates a pre-emptive "Flight Plan" for a task.
- `get_relevant_rules`: Discovery — Fetches laws for a specific file path before editing.
- `validate_architecture_compliance`: Executes a workspace or hunk-aware scan.
- `apply_architectural_remediation`: Returns structured, context-rich fix instructions.
- `get_rule_rationale`: Fetches the reasoning behind a law.
- `get_dependency_graph`: Visualizes module coupling and identifies leaks.

## Layer 4: The v3.0 Governance Runtime Environment (GRE)
The ultimate technical target for Aegis is absolute native enforcement via **I/O Middleware**.

### 4.1 Speculative Virtual File System (V-FS)
An in-memory sandbox that captures proposed code changes and executes AST scans *before* they are committed to the physical disk.

### 4.2 Hardened Tool Proxies
- `aegis_write_file`: Intercepts and blocks non-compliant writes in-flight.
- `aegis_read_file`: Injects ambient architectural DNA into the agent's context window.

## Layer 5: Active Law Matrix
Current active rules are defined in `.aegis/rules/*.yaml`.
