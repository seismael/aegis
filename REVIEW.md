# Aegis Agentic Integration Review

**Date:** May 21, 2026
**Methodology:** Dogfooding investigation — ran all agentic flows (CLI, MCP, skills, prompts) through 3 parallel explore agents, analyzed every user-facing surface for native agentic coding tool integration.

---

## Executive Summary

Aegis has a genuinely differentiated architecture: 4 intent-driven meta-tools, 6 ambient context resources, structured Pydantic return types, in-memory code evaluation, plugin SDK, and a remediation engine. However, the **meta-tool facade was applied incompletely** — every MCP prompt, every skill, and several return paths reference the old 22-tool API. The result: every agentic flow is broken at first use. Agents calling the tools they're told to call get "tool not found" errors.

Additionally, 7 private methods (including the critical `_evaluate_code_delta` for mid-thought validation) are orphaned — registered on the kernel but reachable through no meta-tool. Structured model fields default to 0/null and are never populated, making the structured returns useless for agent decision-making.

The CLI has secondary UX issues: no `--json` output for `check`, inconsistent output styling, silent auto-baseline.

**Core problem**: The meta-tool refactor was ~80% complete. The remaining 20% (prompts, skills, error paths, model population) is what makes the difference between "tools exist" and "tools work."

---

## Part 1: What's Genuinely Good

These are the foundations that make Aegis differentiated. Do not regress these.

### 1a — Meta-Tool Facade (Architecture)
4 intent-driven meta-tools replacing 22 granular tools:
- `plan_architecture(intent?, file_path?)` — task alignment + file context
- `validate_workspace(scope, phase?, category?, auto_fix?)` — compliance + remediation
- `evolve_ruleset(action, target?, rationale?, rules_yaml?)` — full rule lifecycle
- `query_knowledge_graph(query_type, target?)` — introspection

This is the right pattern. 4 tools consume ~400 tokens vs ~2000 for 22. Intent-driven naming maps to what agents want to do, not how it's implemented.

### 1b — Ambient Context Resources (6 resources)
- `aegis://context/{path}` — file-specific rules (proactive discovery)
- `aegis://rules` — full rule dump
- `aegis://baseline` — technical debt ledger
- `aegis://evolution` — rule evolution log
- `aegis://context` — agent handoff snapshot
- `aegis://spec` — architecture spec

### 1c — Structured Return Models (`kernel/models.py`)
`ComplianceResult`, `CodeDeltaResult`, `RelevantRulesResult`, `ServerStatusResult`, `DependencyGraphResult`, `AgentHandoffContext` — all Pydantic, all serializable via `.model_dump_json()`. FastMCP serves these as native JSON to agents.

### 1d — Infrastructure Robustness
- RegexAnalyzer, TreeSitterAnalyzer, GraphAnalyzer — all work correctly
- BaselineManager — thread-safe, atomic writes, signature-based matching
- EvaluationService — 3 evaluation modes (workspace, changes, code_string)
- RemediationPromptSynthesizer — generates structured fix instructions
- FixerRegistry — 2 built-in fixers (BareExceptFixer, PrintToLoggerFixer)

### 1e — Rule Pack System
17-pack taxonomy, RulePackManager with install/remove/update/reset, custom packs, lifecycle hooks, CLI sub-commands.

---

## Part 2: Critical Issues (Blocking Agentic Integration)

### P2.1 — All 6 MCP Prompts Reference Nonexistent Tools

Every prompt tells agents to call old 22-tool names that don't exist:

| Prompt | References | Should reference |
|--------|-----------|-----------------|
| `start-new-task` | `propose_architectural_steering`, `get_active_context` | `plan_architecture` |
| `evaluate-architecture` | `validate_architecture_compliance`, `list_evaluation_phases`, `get_phase_mapping` | `validate_workspace`, `query_knowledge_graph` |
| `remediate-violations` | `apply_auto_fixes`, `validate_architecture_compliance`, `apply_architectural_remediation` | `validate_workspace` |
| `explain-rule` | `get_rule_rationale` | `query_knowledge_graph(query_type="rationale")` |
| `initialize-governance` | `hypothesize_workspace_architecture`, `initialize_project_governance`, `install_rule_pack`, `capture_architectural_baseline` | `plan_architecture`, `evolve_ruleset` |
| `inspect-dependency` | `get_dependency_graph` | `query_knowledge_graph(query_type="dependency")` |

**Impact**: Every agent that follows prompts gets "tool not found" errors. The product is unusable for first-time agentic users.

### P2.2 — All 6 Skills Reference Nonexistent Tools

All `.claude/skills/*.md` files encode expert workflows but every MCP path points to old tool names. 14+ broken references across 6 files. An agent loading any skill gets misled into calling nonexistent tools.

**Impact**: The skills, which are the product's secret sauce (pre-commit edit loop, rule crafting workflow, governance scorecard), are completely non-functional.

### P2.3 — 7 Private Methods Orphaned (Unreachable)

These methods exist on the kernel but no meta-tool dispatches to them:

| Method | Function | Why It Matters |
|--------|----------|---------------|
| `_evaluate_code_delta` | Validates code string in-memory before disk write | **Critical**: Aegis's primary agentic differentiator — mid-thought validation. Without it, agents can only validate after writing to disk. |
| `_get_relevant_rules` | Returns ALL rules for a file path | Different from `_get_active_context` (returns top 5). Full list needed for comprehensive scoping. |
| `_list_evaluation_phases` | Lists phases with rule counts | Needed for CI/CD scoping decisions |
| `_get_phase_mapping` | Shows category→phase mapping | Needed for understanding when rules fire |
| `_update_rule_packs` | Updates installed packs | No way to update packs through MCP |
| `_reset_rule_packs` | Removes all packs | No way to reset through MCP |

**Impact**: 6 of 7 are useful functionality agents should access. `_evaluate_code_delta` is the single most important missing piece.

### P2.4 — `_apply_architectural_remediation` Return Type Mismatch (Runtime Crash)

Signature: `async def _apply_architectural_remediation(self) -> RemediationResult`

Error paths: `return error(...)` which returns `dict` (via `{"success": false, ...}`)

FastMCP tries to serialize the `dict` as a `RemediationResult`. The dict lacks fields like `summary`, `violations_count`, `proposals`, `handoff_prompt`. FastMCP will either crash or return a corrupted object.

**Impact**: When the container is degraded (no governance service), calling `validate_workspace` on a non-compliant project crashes the MCP server.

### P2.5 — `ServerStatusResult` Hardcoded Counts Wrong

- `resources_count=4` — actual: 6 resources registered
- `prompts_count=5` — actual: 6 prompts registered

**Impact**: Agents use these counts to decide whether to explore resources. Seeing 4, they miss 2. Also signals unreliable metadata.

### P2.6 — `RuleInfo.active_violations` and `baseline_entries` Always 0

Both fields default to `0` and are NEVER populated. Every rule returned by `get_active_context` or `get_relevant_rules` shows zero violations and zero baselines, regardless of reality.

**Impact**: Agents cannot prioritize which rules need attention. Decision tree: "is this rule a problem?" → `active_violations > 0` → always false → skip everything.

### P2.7 — `ViolationInfo.mode` Always "block"

Default value `"block"` is never populated from actual rule mode. A `REPORT`-level rule's violations show as `mode: "block"`. The agent treats all violations as critical, inflating `blocking_violations` count.

**Impact**: Agents can't distinguish urgent vs informational violations. 500 report violations = agent spins trying to fix non-blocking issues.

---

## Part 3: Significant UX Issues

### P3.1 — CLI `check` Has No `--json` Flag

`status` has `--json`. `check` doesn't. CI/CD pipelines parsing check output must regex-match `"- MODE file:line (rule_id)"` format.

### P3.2 — Auto-Baseline Is Silent

`governance_service.capture_baseline` runs silently in `check` when `auto_baseline` is enabled (lines 383-387). User sees "0 violations" but doesn't know they were auto-captured as technical debt.

### P3.3 — `install` Command Uses `print()` Not Rich

The `install` command (line 297-308) uses raw `print()` instead of `self.console.print()`. Inconsistent with every other command.

### P3.4 — `apply` Returns Exit 0 on Failure

When `apply` fails (no rules, no violations), it exits 0. Inconsistent with `check`/`fix`/`evolve` which raise `typer.Exit(code=1)`.

---

## Part 4: Correctness Issues (Deserve Investigation)

These surfaced during testing — not fully verified but flagged for investigation:

- `ScopeFilter._path_matches_pattern` uses `str.find` for `**` matching — can produce false positives on Windows absolute paths where `\` appears in path strings
- `_evaluate_code_delta` catches tree-sitter exceptions silently — no way for agent to know if analysis was degraded
- `BaselineManager.load_baseline_raw` silently returns empty list on JSON parse error — corruption invisible to user
- `PolicyParser` ID-less rules write to `None` dict key — only last one logged, others silently lost

---

## Part 5: Removed / Deferred Items (Not Actionable)

These came from the older strategic assessment but are **not the current focus**:

| Item | Reason for Deferral |
|------|-------------------|
| Fix broken rules (arch-import-groups, test-naming-convention, etc.) | Rule content changes, not agentic integration. Separate workstream. |
| CI doesn't run tests | Infrastructure concern, not agentic-native integration. |
| No rule YAML schema documentation | Documentation gap, not architecture. |
| README needs rewrite | Marketing/docs, not integration. |
| Concurrent baseline corruption | Not triggered in practice. Low priority. |
| TreeSitter import crash | Edge case on missing C extension. Low frequency. |
| `mcp>=0.1.0` pin is loose | Dependency management. Not agentic UX. |
| Plugin SDK docs | Niche feature. Not blocking. |

---

## Implementation Priority

| Priority | Item | Phase | Effort |
|----------|------|-------|--------|
| P0 | Fix 6 MCP prompts (P2.1) | Core | Small (text changes) |
| P0 | Add orphaned methods to meta-tools (P2.3) | Core | Small (dispatch wiring) |
| P0 | Fix return type mismatch (P2.4) | Core | Tiny (wrap error in RemediationResult) |
| P0 | Rewrite 6 skills (P2.2) | Core | Medium (6 files, patterns clear) |
| P1 | Populate RuleInfo fields (P2.6) | Models | Small (2 queries per call) |
| P1 | Populate ViolationInfo.mode (P2.7) | Models | Tiny (lookup in rule_map) |
| P1 | Fix ServerStatusResult counts (P2.5) | Accuracy | Tiny (update literals) |
| P2 | Add `check --json` (P3.1) | CLI | Small |
| P2 | Make auto-baseline visible (P3.2) | CLI | Tiny (one print) |
| P2 | Fix `install` Rich styling (P3.3) | CLI | Tiny |
| P2 | Fix `apply` exit code (P3.4) | CLI | Tiny |
| P3 | Investigate correctness issues (P4) | Quality | Medium |

**Total effort**: ~1-2 days for P0-P1, +1 day for P2, +investigation time for P3.
