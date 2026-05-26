# Aegis V4 Project Review & Evaluation

**Date:** Wednesday, 27 May 2026
**Status:** In-Progress Analysis
**Core Vision:** Agent-Native Governance Protocol for AI Agent Harnesses.

## 1. Executive Summary

Aegis V4 presents a paradigm shift from traditional OS-level governance (git hooks, CI gates) to **Agent-Native Governance**. By living inside the AI agent's cognition loop via the Model Context Protocol (MCP), it enables JIT architectural enforcement that is self-healing and stateless.

### Core Strengths
- **Microkernel Architecture:** Clean separation between Policy, Evaluation, and Observability.
- **MCP-Native:** Seamlessly integrates with modern AI IDEs and agents (Claude Code, Aider).
- **Multi-Engine Routing:** Orchestrates AST (Tree-sitter), Graph, Regex, and Semantic analyzers for comprehensive coverage.
- **Statelessness:** Leverages the agent's context window for session state, reducing architectural overhead.
- **Polyglot Support:** Tree-sitter integration for Python, TypeScript, JavaScript, and Rust.

### Significant Gaps & Risks
- **Gemini Integration:** Currently no native installer or wrapper for Gemini CLI or other Google-harness agents.
- **Semantic Engine (PoC):** The `SemanticAnalyzer` is a Proof-of-Concept using simple heuristics rather than actual re-entrant LLM calls.
- **Installer Scope:** `aegis install` is limited to Claude and Aider; it lacks a universal or pluggable plugin system for new harnesses.
- **User Experience:** The "intuitive agent-native experience" is heavily dependent on `customInstructions` which can be brittle if the agent ignores them.
- **Performance:** Graph analysis on large workspaces may become a bottleneck if not optimized for incremental updates.

---

## 2. Architectural Deep-Dive

### 2.1 The MCP Surface
The 6 core tools provided by the `AegisKernel` cover the essential lifecycle of governance:
- `validate_architecture_compliance`: The mandatory gate.
- `plan_architecture`: Pre-emptive alignment.
- `request_semantic_grading_rubric`: Re-entrant self-evaluation.
- `scaffold_governance_framework`: Initial setup.
- `query_knowledge_graph`: Deep introspection.
- `evolve_ruleset`: Lifecycle management.

**Evaluation:** The tool surface is well-designed and covers the "Plan -> Act -> Validate" loop perfectly.

### 2.2 Evaluation Engines
- **AST:** Strong implementation using `tree-sitter`. Supports positive/negative rules.
- **Graph:** Handles cross-file dependencies and layer violations.
- **Regex:** Fast fallback for simple patterns.
- **Semantic:** **MAJOR GAP.** Currently simulates evaluation. Needs a real implementation that either:
    1. Returns a rubric for the parent LLM (Re-entrant).
    2. Calls a dedicated sub-agent/API for grading.

### 2.3 Policy Layer
Rules are YAML-based, categorized, and phase-aware. The `RulePackManager` effectively handles bundled resources.

---

## 3. Harness Integration Analysis

### 3.1 Claude Code
- **Method:** `~/.claude.json` mutation + `customInstructions`.
- **Status:** Functional.
- **Improvement:** Could benefit from a more robust "Skill" deployment that doesn't just copy markdown files but integrates with Claude's future native tool-calling capabilities.

### 3.2 Aider
- **Method:** `~/.aider.conf.yml` mutation + `--test-cmd` hijack.
- **Status:** Functional (self-healing loop).
- **Improvement:** Aider's `--test-cmd` is a "brute force" approach; a native MCP integration within Aider would be cleaner.

### 3.3 Gemini CLI (Planned)
- **Status:** **NOT IMPLEMENTED.**
- **Requirements:** 
    - Installer needs to support `~/.gemini.json` or equivalent.
    - Specialized `customInstructions` or "System Prompts" for Gemini.
    - Verification of Gemini's MCP support stability.

---

## 4. Required Capabilities (The "Gaps")

1. **Universal Harness Wrapper:** A generic `HarnessInterface` in `installer.py` to allow easy addition of new agents (Gemini, OpenCode, etc.).
2. **Production-Grade Semantic Engine:** Transition from heuristic PoC to a true re-entrant rubric-based system where the agent is forced to "show its work" for semantic rules.
3. **Agent-Native Instruction Generation:** Automatically generate and update `.claude.md`, `GEMINI.md`, and `AGENTS.md` in the workspace root to ensure any entering agent (Claude, Gemini, etc.) immediately "wakes up" to the governance protocol.
4. **Incremental Graph Analysis:** Cache import graphs to prevent O(N) scans on every validation call.
5. **Cross-Agent Memory:** While Aegis is stateless, a thin `.aegis/session.json` could help coordinate between different agents (e.g., Aider and Claude) working on the same repo.

---

## 5. Conclusion & Action Plan

Aegis V4 is architecturally sound but currently limited in its "reach." To achieve the vision of a **universal agent-native governance protocol**, we must:

1. **Implement Gemini Integration:** Update `AgentNativeInstaller` to support Gemini.
2. **Upgrade Semantic Engine:** Finalize the re-entrant rubric logic.
3. **Refactor Installer:** Move to a plugin-based harness system.
4. **Validation:** Add integration tests for multi-harness scenarios.
