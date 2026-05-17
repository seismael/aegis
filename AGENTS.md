# Aegis Agentic Operational Invariants

## Governance Protocol
- Run `uv run aegis check` at the end of each logical task (before commit or when a feature is complete). Blocking violations must be resolved.
- Teams may opt out by removing this line; the system gracefully degrades to manual `/aegis-evaluate` invocations and Git pre-commit hooks.
- Run `uv run aegis status` to inspect the current rule matrix and debt ledger.
- Baseline new or unavoidable violations with `uv run aegis baseline` (never suppress silently).

## Development Workflow
- **Test-Driven Development**: Write tests before feature logic. Run `uv run pytest tests/` after every change.
- **Linting**: Format and lint with `ruff check --fix && ruff format` before every commit.
- **Architecture**: Strict hexagonal architecture (Domain -> ports <- Infrastructure). Domain layer must never import from infrastructure.
- **Engine-Type Awareness**: When adding rules, choose the correct engine_type (tree-sitter for AST structure, graph for cross-file dependencies, regex for pattern matching).

## MCP Tools (AI Agent Integration)
- Use `validate_architecture_compliance` to scan the full workspace.
- Use `apply_architectural_remediation` to get structured fix instructions for active violations.
- Use `get_rule_rationale` to trace why a rule exists and its evolution history.
- Use `get_dependency_graph` to inspect module coupling.
- Use `server_status` for a health overview including counts of rules, tools, and violations.

## MCP Resources (Data Access)
Read-only governance artifacts exposed as MCP resource URIs:
- Read `aegis://rules` for the full rule matrix (rules.yaml).
- Read `aegis://baseline` for the architectural debt ledger (baseline.json).
- Read `aegis://evolution` for rule evolution history (evolution_log.json).
- Read `aegis://spec` for the architecture specification (SPEC.md).

## MCP Prompts (Workflow Templates)
Reusable prompt templates for common agentic workflows:
- `evaluate-architecture` — Full compliance scan → remediate → re-validate loop.
- `remediate-violations` — Step-by-step violation fix workflow.
- `explain-rule` — Fetch rationale + evolution history for a specific rule.
- `inspect-dependency` — Analyze module coupling and detect leaks.

## Server Configuration
The MCP kernel supports three transports:
- `stdio` (default) — Standard input/output, ideal for Claude Desktop / CLI integration.
- `sse` — Server-Sent Events over HTTP for remote agent connections.
- `streamable-http` — Full HTTP transport with streaming support.

Run with: `uv run aegis-kernel --transport sse --host 0.0.0.0 --port 8000`

## Plugin System
- Drop Python modules into `.aegis/plugins/*.py` — they auto-load on next CLI command.
- Each plugin can expose two optional hooks:
  - `register_analyzers() -> list[ASTAnalyzerInterface]` — custom code analyzers.
  - `register_mcp_tools() -> list[Callable]` — custom MCP tools for AI agents.
- Plugin errors are logged and never crash the engine.
- Run `uv run aegis plugins` to see what's loaded.
- Run `uv run aegis status` to see the plugin count in the summary.

## Universal Installer
- Run `uv run aegis install` once per machine to register the Aegis MCP server globally.
- This injects into `~/.claude/claude_desktop_config.json` and `~/.aider.conf.yml`.
- Agentic skills are deployed to `~/.claude/skills/`, making `/aegis-*` commands available in any Claude Code session.
- The installer is idempotent — safe to re-run. Existing configs are preserved.

## Self-Governance
- Aegis enforces OOD, hexagonal isolation, docstring completeness, and import hygiene on its own source code.
- The project must remain self-compliant with zero active violations at all times.
