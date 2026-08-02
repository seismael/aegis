# Aegis Token Efficiency — Real Agent Validation

**Date**: 2026-08-02 | **Agents tested**: Claude Code, Gemini CLI, OpenCode
**Method**: Paired controlled trials — identical TaskFlow DDD project, identical T2 prompt, with/without Aegis governance

---

## Executive Summary

Aegis V4 was tested against real coding agents (Claude Code with deepseek-v4-pro, Gemini CLI with gemini-3.5-flash, OpenCode) performing a cross-layer feature addition task. Results show that Aegis token efficiency is **agent-dependent**:

- **Gemini CLI**: +35.5% input token savings (390K vs 605K)
- **Claude Code**: -28.6% overhead (126K vs 98K)
- **OpenCode**: AGENTS.md alone (no MCP) has zero effect

The previously claimed 86.6% and 83.7% savings were based on simulated benchmarks and are **not reproducible** in real agent trials.

---

## Methodology

### Test Setup
- **Project**: TaskFlow — a Python DDD task management system with 133 seeded architectural violations across 25 files
- **Rules**: 68 rules across 5 packs (architecture, security, best-practices, style, testing)
- **Task (T2)**: "Add email notification. The email service is in infrastructure/email.py. Keep the domain clean — no direct domain→infrastructure dependency."
- **MCP**: Aegis kernel MCP server registered via wrapper script, providing check_architecture and other tools

### Agent Configurations

| Agent | Model | Flags |
|:---|:---|:---|
| Claude Code | deepseek-v4-pro | `-p --output-format json --dangerously-skip-permissions` |
| Gemini CLI | gemini-3.5-flash | `-p --output-format json --approval-mode yolo` |
| OpenCode | deepseek-v4-pro | `run` mode (no MCP support) |

### Measurement
- **Token counts**: Extracted from JSON output (`usage.input_tokens`, `usage.output_tokens`, `stats.models.*.tokens`)
- **Violations**: Measured via in-process Aegis headless check (68 rules, Tree-sitter, Graph, Regex analyzers)

---

## Results

### Claude Code (deepseek-v4-pro)

| Metric | WITH Aegis | WITHOUT Aegis | Delta |
|:---|:---|:---|:---|
| Input tokens | 102,367 | 89,063 | +15% |
| Output tokens | 23,749 | 9,029 | +163% |
| **Total tokens** | **126,116** | **98,092** | **-28.6%** |
| Turns | 54 | 43 | +26% |
| Cost | $1.99 | $1.12 | +$0.87 |
| check_architecture called | 1 time | 0 times | — |
| Violations | 133→141 (+8) | N/A* | — |

*Without-Aegis trial had no rules installed for baseline measurement.

### Gemini CLI (gemini-3.5-flash)

| Metric | WITH Aegis | WITHOUT Aegis | Delta |
|:---|:---|:---|:---|
| **Input tokens** | **390,544** | **605,825** | **+35.5% savings** |
| Candidates (output) | 8,100 | 8,790 | +8% |
| Total tokens (all models) | 4,650,189 | 5,321,643 | +12.6% savings |
| Tool calls | 85 | 84 | — |
| Lines added | +98 | +149 | -34% |
| Lines removed | -8 | -5 | — |

### OpenCode (deepseek-v4-pro, run mode — no MCP)

| Metric | WITH AGENTS.md | WITHOUT AGENTS.md |
|:---|:---|:---|
| Violations before | 133 | 133 |
| Violations after | **139 (+6)** | **139 (+6)** |
| Duration | 180s | 155s |
| Output | 24KB | 20KB |
| **Effect** | **None** (MCP not available in run mode) | — |

---

## Analysis

### Why Gemini Saved Tokens, Claude Didn't

1. **Gemini with Aegis**: CLAUDE.md/AGENTS.md with governance instructions focused Gemini on the specific task, reducing unnecessary exploration. The agent added 34% fewer lines of code (98 vs 149), suggesting tighter scoping.

2. **Claude with Aegis**: The governance instructions added to the system prompt increased input tokens. The check_architecture MCP call added turns. The agent was MORE thorough (54 turns vs 43), which increased output tokens but did not produce measurably better code.

3. **OpenCode**: Without MCP tools, AGENTS.md instructions have zero effect on agent behavior. The agent cannot call check_architecture in `run` mode.

### Key Insight

Aegis does not uniformly reduce tokens. Its effect depends on:
- The agent/model's response to governance instructions
- Whether MCP tools are available and used
- The complexity of the task vs. the overhead of rule checking

---

## Previous Claims (Invalidated)

| Claim | Claimed | Actual (Claude) | Actual (Gemini) | Valid? |
|:---|:---|:---|:---|:---|
| 86.6% reduction (architectural drift) | Simulated | -28.6% | +35.5% (input) | ❌ Not reproducible |
| 83.7% reduction (AST delta check) | Simulated | — | — | ❌ Not tested |
| Neutral overhead for compliant tasks | Simulated | — | — | ❌ Not tested |

The simulated benchmarks used hardcoded token counts without real LLM calls. Real-world results are **mixed** and **agent-dependent**.

---

## What Aegis Actually Provides

Aegis is **not** primarily a token saver. It is a **governance engine** that provides:

1. **Violation detection**: 133 violations across 25 files in 0.32s (68 rules, 5 packs)
2. **Plan gate**: Catches wrong-layer imports before code generation
3. **Enforcement node**: In-memory AST delta evaluation in microseconds
4. **Executor**: Blocks writes with CRITICAL/HIGH violations
5. **MCP gate**: Full workspace compliance sweep via check_architecture

Token efficiency is a **secondary effect** that varies by agent and model.
