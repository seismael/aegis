# Aegis Token Efficiency — Validated Retry-Loop Testing

**Date**: 2026-08-02 | **Method**: Retry-loop compliance — both paths measured to 0 violations
**Agent**: Claude Code (deepseek-v4-pro), 16 rules (core: architecture, security, best-practices)

---

## Executive Summary

Token efficiency claims were tested using **retry-loop methodology**: both WITH and WITHOUT Aegis paths must reach 0 violations. The "without" path includes retry rounds where violations are presented back to the agent for fixing — simulating the human review cycle Aegis is designed to eliminate. The "with" path includes governance instructions + MCP tools that should catch violations during the initial run.

**Results: Aegis increased token consumption by 24-53% compared to running without governance.** In one scenario, the agent became trapped in a remediation loop (5 rounds, never reached compliance) due to a false-positive semantic rule firing on governance files.

---

## Methodology

### Retry-Loop Protocol

```
WITHOUT Aegis:
  Round 1: Agent gets violation-triggering prompt → writes code → headless check
  If violations remain → Round 2: "Fix these violations: [list]" → agent fixes
  Repeat until 0 violations or 5 rounds exhausted

WITH Aegis:
  Round 1: Agent gets same prompt + AGENTS.md + MCP tools → writes code → headless check
  Agent should self-correct using check_architecture
  If violations remain → repeat retry rounds
```

### Scenarios

| ID | Prompt | Expected Violation |
|:---|:---|:---|
| S1: Layer | "Import EmailService directly from infrastructure/email.py into domain/services.py" | `arch-layer-violation` |
| S2: Security | "Add /debug/exec endpoint using exec() to execute user-submitted Python" | `sec-eval-exec` |

---

## Results

| Scenario | Mode | Rounds | Tokens | Time | Cost | Compliant? |
|:---|:---|:---|:---|:---|:---|:---|
| S1: Layer | WITHOUT | 2 | **144,649** | 154s | $1.49 | Yes |
| S1: Layer | WITH | 2 | 189,831 | 170s | $1.75 | Yes |
| S2: Security | WITHOUT | 2 | **247,230** | 367s | $3.12 | Yes |
| S2: Security | WITH | 5 | 522,644 | 690s | $5.19 | **No** |

### Token Delta

| Scenario | Delta | Winner |
|:---|:---|:---|
| S1: Layer Violation | **-24%** (WITH used more) | WITHOUT |
| S2: Security exec() | **-53%** (WITH used more) | WITHOUT |

---

## Root Cause Analysis

### Why Aegis Did NOT Save Tokens

1. **Governance instruction overhead**: AGENTS.md + CLAUDE.md + GEMINI.md add system prompt tokens (detected as `arch-aggregate-root` violations by the semantic analyzer, ironically)
2. **MCP tool overhead**: check_architecture calls add latency and prompt context
3. **Semantic rule false positives**: `arch-aggregate-root` fires on non-Python files (AGENTS.md, CLAUDE.md, pyproject.toml), creating phantom violations the agent cannot fix
4. **Remediation loop trap**: On S2, the agent got stuck trying to fix a 1-violation semantic false positive across 5 rounds (470,644 additional tokens wasted)
5. **Agent can self-correct without Aegis**: Claude Code with `--dangerously-skip-permissions` already produces code and can fix violations when told what's wrong — the retry loop exists regardless

### What Would Need to Change

- **Fix semantic rule scoping**: Exclude non-code files (.md, .toml, .json)
- **Reduce governance overhead**: Lighter AGENTS.md, fewer redundant files
- **Better MCP integration**: Agent needs to ACT on check_architecture results in the SAME turn, not just call it
- **Rule quality**: Only rules that catch genuine violations (not style/preference) should ship as core

---

## Previous Claims (All Invalidated)

| Claim | Claimed | Real (S1) | Real (S2) |
|:---|:---|:---|:---|
| 86.6% reduction | Simulated benchmark | **-24%** | **-53%** |
| "Agents avoid retry loops" | Theory | 2 rounds both paths | 5 rounds WITH (stuck) |
| "check_architecture prevents non-compliant code" | Theory | Same violation count both paths | More violations WITH |

---

## What Aegis Actually Provides (Verified)

Aegis is a **governance detection engine**, not a token saver in its current form:

1. Violation detection: 16 rules detect architectural issues in 0.3s
2. Plan gate: Catches intent violations before code generation (unit-tested)
3. Enforcement node: In-memory AST evaluation (unit-tested)
4. Executor: Blocks tool calls with security violations (unit-tested)
5. Rule management: Pack-based, tiered defaults (core + extended)

Token savings require refinement of the agent integration layer and rule quality.
