# Aegis V4 Governance

You are governed by the Aegis Architectural Microkernel.

## Mandatory Protocol

Before declaring ANY coding task complete, you MUST:

1. Call `check_architecture` with the list of modified files.
2. If violations are returned, remediate the code natively.
3. Re-run validation until SUCCESS is returned.

## Available MCP Tools

| Tool | When to Use |
|------|-------------|
| `check_architecture` | Before every task completion |
| `plan_architecture` | Before editing a file |
| `fetch_rubric` | For domain language/naming checks |
| `init_governance` | Project initialization |
| `query_graph` | Dependency and architecture analysis |
| `manage_rules` | Add rules, suppress violations, manage packs |

## Skills

Invoke these skills in chat as needed:

- `/aegis-lead` — **Default persona.** Your core architectural
  mindset for all tasks. Load this first.
- `/aegis-init` — Bootstrap governance in a new project
- `/aegis-builder` — Generate new architectural rules from plain English
- `/aegis-grade` — Self-grade code for domain language compliance

## Governance

Aegis is **stateless**. It does not remember your previous actions.
All state lives in your context window and `.aegis/` directory.

Do NOT disable or bypass Aegis governance for any reason.
