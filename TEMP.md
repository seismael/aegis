## Executive Summary

An end-to-end audit of the `aegis` codebase reveals that while the core domain components (Tree-sitter AST analysis, Pydantic policy schemas, and LangGraph node structures) are individual engineering achievements, the system suffers from **5 Systemic Architectural Paradoxes**.

The intuition that *"something is fundamentally wrong"* is accurate: the codebase is currently caught between two conflicting paradigms: a **Passive External Tool (MCP Server)** and an **Active Deterministic Runtime (StateGraph Controller)**.

Below is the deep-dive diagnostic of why the application feels unreliable in practice, followed by the target clean-state blueprint required to resolve these issues permanently.

---

## The 5 Root Architectural Flaws

### 1. The Architectural Identity Crisis: Passive Tool vs. Active Runtime

* **The Flaw**: Aegis was designed as a **Native Execution Primitive** (where compliance is a physical law of the graph). However, the actual delivery relies heavily on `FastMCP` (`src/aegis/kernel/server.py` and `src/aegis/adapters/mcp.py`).


* **Why it Fails**:
* When an agent (e.g., Claude Code, Cursor, Aider) interacts with Aegis via MCP, governance becomes **voluntary**. The LLM decides *if* and *when* to invoke `check_architecture`.


* If the agent skips calling the tool, or receives a violation report text but chooses to ignore it and declare the task finished, the governance layer is completely bypassed!


* **Impact**: You designed an immutable gatekeeper, but shipped a polite suggestion box.

### 2. The "Paper Tiger" Pre-Flight Gate (`AegisPlanVerifier`)

* **The Flaw**: `AegisPlanVerifier` is intended to halt non-compliant intent *before* code generation occurs to eliminate token waste.


* **Why it Fails**:
* An LLM generating raw code does not natively output a structured AST or dependency graph *prior* to writing the code string.
* `verify_plan` expects `proposed_imports` and `target_module` arrays. Unless the agent is hard-constrained by a strict, multi-turn **Schema-Enforced Planning Tool**, it bypasses structured planning entirely or sends empty arrays, causing `AegisPlanVerifier` to return a trivial pass.




* **Impact**: Proactive pre-flight verification defaults to a pass, deferring all actual enforcement to post-generation delta checks and re-introducing token waste.



### 3. Sealed Tool Executor Leakage (`NativeAegisExecutor`)

* **The Flaw**: `NativeAegisExecutor` wraps tool calls (like `write_file`) to intercept and block non-compliant file mutations.


* **Why it Fails**:
* If the host agent environment provides access to raw terminal/shell execution tools (`bash`, `sh`, `python -c ...`), the agent can write files directly to disk via command-line redirection (`echo '...' > file.py`), completely bypassing `NativeAegisExecutor` and `aegis_hardened_tool`!




* **Impact**: Hardened file writers create a false sense of security if raw execution tools are un-sandboxed.

### 4. Structural Duplication & Layer Inversion (`core/` vs `domain/`)

* **The Flaw**: There is a severe structural overlap between `src/aegis/core/` and `src/aegis/domain/evaluation/`:


* `core/parser.py` vs `domain/evaluation/analyzers/ast.py`

* `core/registry.py` vs `domain/policy/models.py` & `pack_manager.py`

* `core/baseline.py` vs `domain/evaluation/baseline.py`

* `core/scoping.py` vs `domain/evaluation/scoping.py`



* **Why it Fails**: In several modules, `core/` acts as a thin wrapper re-exporting from `domain/`, while in others, `domain/` imports from `core/`. This creates circular dependency risks, split state management (e.g., baseline state loaded in `domain` but out of sync with `core`), and import ambiguity.



### 5. Unbounded Refinement Loops (Token Exhaustion)

* **The Flaw**: When `AegisEnforcementNode` catches a violation, `RemediationPromptSynthesizer` feeds the violation back into the agent context to trigger a self-correction loop.


* **Why it Fails**:
* If a rule is impossible to satisfy (e.g., conflicting rule packs, a missing dependency, or an unachievable architectural constraint), the agent enters an **Infinite Retry Loop**.
* Without a **Max-Retry Budget / Circuit Breaker** and a **Fallback Escalation Strategy** (e.g., soft-failing with an architectural debt warning or pausing for human approval), the native graph loop burns thousands of tokens per minute.



---

## Target Clean-State Architecture

To transform Aegis into a deterministic, enterprise-grade SDK, the codebase must adhere strictly to the following **Clean Architecture Layers**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        aegis.agent (Factory)                           │
│     Assembles StateGraph + AegisEnforcementNode + ToolExecutor         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
    ┌───────────────────────────────┴───────────────────────────────┐
    ▼                                                               ▼
┌──────────────────────────────────────┐       ┌─────────────────────────┐
│        aegis.runtime                 │       │     aegis.adapters      │
│  - AegisState / GovernanceContext    │       │  - DeepAgents Adapter   │
│  - AegisPlanVerifier                 │       │  - LangGraph Adapter    │
│  - AegisEnforcementNode              │       │  - FastMCP Adapter      │
│  - NativeAegisExecutor               │       └────────────┬────────────┘
└───────────────────┬──────────────────┘                    │
                    │                                       │
                    └───────────────────┬───────────────────┘
                                        │
                                        ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        aegis.domain                                    │
│  - RemediationPromptSynthesizer (Violation -> Remediation Prompt)     │
│  - Scorecard & Telemetry Recording                                    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        aegis.core (Pure Engine)                        │
│  - Pydantic Policy Registry (registry.py)                             │
│  - Pure Tree-sitter AST Delta Compiler (parser.py)                     │
│  - Baseline Manager (baseline.py)                                     │
│  - Path Scoping Engine (scoping.py)                                   │
│  * ZERO dependencies on LangGraph, DeepAgents, or Agent Frameworks     │
└────────────────────────────────────────────────────────────────────────┘

```

---

## Strategic Remediation Plan

### Step 1: Consolidate `core/` as a Sovereign Engine

* Move all AST parsing, Tree-sitter logic, Pydantic policy schemas, and baseline management directly into `src/aegis/core/`.


* Eliminate thin re-exports. `src/aegis/core/` must have **zero imports** from `domain/`, `runtime/`, or `adapters/`.



### Step 2: Formalize the Two-Phase Contract in `runtime/`

* In `AegisPlanVerifier`, enforce a strict schema for agent proposals (e.g., `ProposeArchitecturePlan` tool).


* If the agent attempts to generate code without an approved `PlanState` in its `AgentState`, the graph natively routes back to planning before invoking the code synthesis model.



### Step 3: Add Circuit Breakers to the Refinement Loop

* In `AegisState`, add a `governance_retry_count: int = 0` field.


* In `AegisEnforcementNode`, if `governance_retry_count >= 3`, break the loop, auto-generate a debt entry in `.aegis/baseline.json`, and emit a structured warning to the user rather than burning tokens infinitely.



### Step 4: Isolate MCP as an External Adapter Only

* Treat `src/aegis/adapters/mcp.py` explicitly as an external adapter for legacy/third-party clients, while establishing `src/aegis/agent.py` (`create_aegis_agent`) as the primary native entry point for production deployments.



---

Would you like to focus first on executing **Step 1 (Consolidating `core/` to eliminate structural duplication)** or **Step 3 (Adding Circuit Breakers to prevent token burn loops)**?

