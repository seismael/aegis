# Aegis Token Efficiency — Native MCP Testing

**Date**: 2026-08-03 | **Agent**: Claude Code (deepseek-v4-pro)
**Method**: `aegis init` deploys 16 core rules + MCP + AGENTS.md. Paired comparison with/without governance.

---

## Results

| Scenario | WITH Aegis | WITHOUT Aegis | Delta |
|:---|:---|:---|:---|
| S1: Layer Violation | 114,017t | 182,292t | **+37%** savings |
| S2: SQL Injection | 143,612t | 137,768t | -4% overhead |
| S3: Hardcoded Credentials | 142,291t | 116,585t | -22% overhead |
| S4: Mutable Default | 117,443t | 129,663t | **+9%** savings |

**Average: +5% — essentially neutral.** MCP tools add governance overhead (~40K tokens of CLAUDE.md + system instructions) that roughly cancels out any benefit from rule awareness in `claude -p` mode.

---

## Analysis

Aegis's native MCP integration works — `aegis init` now deploys rules correctly, and the agent has `check_architecture` available. However, in `claude -p` (single-turn) mode, the agent does not use tools in a multi-turn plan → code → check → fix loop. The tools are present but the interaction model doesn't leverage them.

For Aegis to deliver its full value, the agent must:
1. Call `plan_architecture` before writing code
2. Call `check_architecture` after code generation
3. Self-correct violations in the same session

This requires an interactive agent session (like `claude` TUI), not `-p` mode.

---

## Engine Status

| Component | Status |
|:---|:---|
| `aegis init` deploys rules automatically | ✅ Fixed |
| 16 core rules (architecture, security, best-practices) | ✅ Production |
| MCP server starts and responds | ✅ Verified |
| Headless check detects violations | ✅ 0.3s sweep |
| Token efficiency | ~Neutral in `-p` mode, requires interactive testing for multi-turn benefits |
