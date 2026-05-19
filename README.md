# Aegis — Universal Architectural Governance Protocol

Aegis is a governance engine that enforces architectural rules via AST analysis, regex patterns, and import-graph validation. It integrates as a CLI tool and MCP server, detecting structural drift before it reaches production.

## Installation

```bash
# pip
pip install aegis-governance

# uv
uv tool install aegis-governance

# pipx
pipx install aegis-governance
```

### From source

```bash
git clone https://github.com/seismael/aegis.git
cd aegis
uv sync --dev
```

## Quickstart

```bash
# 1. Register global hooks
aegis install

# 2. Initialize governance in your project
cd my-project
aegis init

# 3. Run governance check
aegis check
```

Example output:

```
$ aegis check
- BLOCK src/domain/order.py:42 (arch-layer-violation)
    Domain layer imports infrastructure module 'db.session'
    Severity: HIGH | Rule: arch-layer-violation

- WARN src/api/routes.py:18 (sec-csrf-protection)
    POST route without CSRF protection
    Severity: MEDIUM | Rule: sec-csrf-protection

- REPORT src/utils/helpers.py:7 (style-consistent-quotes)
    Inconsistent quote style (expected single quotes)
    Severity: LOW | Rule: style-consistent-quotes

Summary: 3 total, 1 blocking.
```

### Strict mode

Exit with code 1 on any violation (not just BLOCK):

```bash
aegis check --strict
```

### Filter by rule

```bash
aegis check --rule arch-layer-violation,sec-jwt-validation
```

### View status

```bash
aegis status
```

### Baseline existing violations

Grandfather existing violations so only new drift is flagged:

```bash
aegis baseline --capture
aegis check
```

## CLI Reference

| Command | Description |
|---|---|
| `aegis init` | Bootstrap `.aegis/` governance directory |
| `aegis check` | Run all rules against the workspace |
| `aegis status` | Show governance health summary |
| `aegis fix` | Auto-remediate fixable violations |
| `aegis evolve` | Accept or reject a proposed rule change |
| `aegis baseline` | Manage the technical debt ledger (capture, show, prune, expire) |
| `aegis apply` | Apply proposed architectural steering |
| `aegis rules list` | List installed rule packs |
| `aegis rules show <pack>` | Show rules in a specific pack |
| `aegis rules install <pack>` | Install a rule pack |
| `aegis serve` | Start the MCP kernel server |

## Rule YAML Schema

Rules are defined in YAML files organized by category under `.aegis/rules/` or `src/aegis/resources/default_rules/`.

### Pack descriptor (`pack.yaml`)

```yaml
name: architecture        # unique pack name
version: 1.0.0
description: Layered architecture invariants
author: Aegis
```

### Rule fields

```yaml
rules:
  - id: arch-layer-violation          # unique rule identifier
    description: >                    # human-readable summary
      Domain layer must not import infrastructure modules
    severity: HIGH                    # LOW | MEDIUM | HIGH | CRITICAL | WARN
    mode: block                       # silent | report | warn | block | fix
    category: architecture            # ruleset taxonomy for phase mapping
    engine_type: regex                # regex | tree-sitter | graph
    language: py                      # py | ts | tsx | js | jsx | rs
    query: ^from\s+infrastructure     # engine-specific query pattern
    applies_to:                       # glob patterns for targeted files
      - "**/domain/**"
    excludes: []                      # glob patterns to exclude
    rationale: >                      # why the rule exists
      Layered architecture requires domain purity
```

### Engine types

- **regex** — Pattern matching via Python `re` module. Use for naming conventions, forbidden patterns, style rules.
- **tree-sitter** — AST-level queries using Tree-sitter query syntax. Use for structural patterns (function definitions, class hierarchies, import statements).
- **graph** — Import-graph analysis. Use for layer violations, circular dependencies, module isolation. Currently Python-only.

### Positive rules (candidates/check)

For rules enforcing "X must have Y" (e.g., every public function must have a docstring):

```yaml
  - id: required-docstrings
    engine_type: tree-sitter
    candidates_query: "(function_definition) @fn"  # all functions
    check_query: "(function_definition body: (block . (expression_statement (string))?) @body)"  # functions with docstrings
```

Violations = candidates minus check results.

## CI/CD Integration

### GitHub Actions

```yaml
name: Governance Check
on: [push, pull_request]
jobs:
  governance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install aegis-governance
      - run: aegis init
      - run: aegis check --strict
```

Exit codes: 0 = clean, 1 = violations found (blocking in strict mode).

### Pre-commit hook

Aegis registers a pre-commit hook during `aegis install` that runs `aegis check` on staged changes.

## MCP Integration

Aegis exposes 22 MCP tools covering the full governance lifecycle. Run the MCP server:

```bash
aegis serve
```

Configure in your MCP client (Claude Code, Cursor, etc.):

```json
{
  "mcpServers": {
    "aegis": {
      "command": "aegis",
      "args": ["serve"]
    }
  }
}
```

Key MCP tools: `initialize_governance`, `evaluate_workspace`, `evaluate_code_delta`, `get_active_context`, `propose_architectural_steering`, `manage_baseline`, `install_rule_pack`.

## Configuration

Aegis reads `.aegis/config.yaml`:

```yaml
version: "1.0"
rules_dir: .aegis/rules
strict: false
phases:
  - pre-commit
  - ci
  - nightly
plugins:
  - name: cloud_isolation
    enabled: true
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Tree-sitter not available` | Missing C extension | `pip install tree-sitter` |
| `No rules found` | Bad rules path | Run `aegis init` to create `.aegis/` |
| `aegis: command not found` | Not on PATH | Use `uv run aegis` or check install |
| Baseline violations not matching | Signature drift | Run `aegis baseline --capture` to refresh |
| MCP connection refused | Server not running | Run `aegis serve` in a separate terminal |

## Project Status

Aegis is in beta. The core engine (regex, tree-sitter, graph analyzers) is production-tested with 92 default rules across 17 categories. The plugin SDK and MCP integration are stable.

## License

Apache License 2.0
