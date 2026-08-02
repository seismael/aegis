# Aegis Native Agent Engine: Architecture & Technical Specification

> **Canonical Source of Truth** for Aegis Agentic Governance Runtime SDK.

---

## 1. Executive Overview & Core Governance Philosophy

Aegis is an **Agent-Native Architectural Runtime Engine & Governance SDK** that transforms software governance from a reactive post-hoc check into a **Proactive, Correct-by-Construction Execution Primitive**.

### The Shift from Reactive to Proactive Governance

| Metric | Traditional Reactive Governance | Aegis Proactive Native Engine |
| :--- | :--- | :--- |
| **Execution Point** | Post-generation (Scans files on disk after write) | **Pre-flight & In-Memory Delta** (Validates plan/code before disk write) |
| **Token Efficiency** | Low (Consumes tokens generating non-compliant code, then retrying) | **Optimal** (Halts bad intent at Plan Gate, saving ~90% of token tax) |
| **Runtime Overhead** | Network/IPC latency or manual human checks | **Microseconds** (In-process Python/Tree-sitter AST delta evaluation) |
| **Integration** | Optional external tool call | **Native Execution Invariant** (Baked into agent `StateGraph` & `ToolExecutor`) |
| **Maintainability** | High drift debt (if hard-forking frameworks) | **Zero Drift Debt** (Native Extension Pattern via inheritance & DI) |

---

## 2. Target Modular Directory Structure

```text
/src/aegis/
├── agent.py            # Unified Factory Entry Point (create_aegis_agent)
├── core/               # Framework-Agnostic Core Engine
│   ├── registry.py     # Pydantic Policy Registry & Loader
│   ├── parser.py       # Pure AST-Delta Compiler (TreeSitterAnalyzer)
│   ├── baseline.py     # Debt Ledger Baseline Manager
│   └── scoping.py      # Path Component Scope Filtering
├── runtime/            # Agentic Runtime Glue
│   ├── state.py        # AegisState & GovernanceContext schemas
│   ├── nodes.py        # AegisEnforcementNode, AegisPlanVerifier, AegisFinalGate
│   ├── executor.py     # NativeAegisExecutor (Sealed I/O Interceptor)
│   └── wrappers.py     # aegis_hardened_tool decorator
├── domain/             # Domain Intelligence & Feedback Loops
│   ├── synthesizer.py  # RemediationPromptSynthesizer
│   ├── evaluation_service.py # EvaluationService orchestrator
│   ├── scorecard.py    # Health Scorecard generator
│   └── telemetry.py    # Telemetry recorder
└── adapters/           # Ecosystem & Platform Adapters
    ├── deepagents.py   # DeepAgentsAdapter
    ├── langgraph.py    # LangGraphAdapter
    └── mcp.py          # FastMCP Microkernel Adapter (AegisKernel)
```

---

## 3. Structural Architecture & Execution Pipeline

```
                                  Agent Intent / User Request
                                               │
                                               ▼
                                 ┌───────────────────────────┐
                                 │   AegisPlanVerifier       │  ◄── 1. Proactive Pre-Flight Gate
                                 │  (Plan / Intent Check)    │      (PolicyParser + GraphAnalyzer)
                                 └─────────────┬─────────────┘
                                               │
                                 ┌─────────────┴─────────────┐
                                 │   Plan Approved / Valid   │
                                 └─────────────┬─────────────┘
                                               │
                                               ▼
                                 ┌───────────────────────────┐
                                 │   Code Generation / Delta │
                                 └─────────────┬─────────────┘
                                               │
                                               ▼
                                 ┌───────────────────────────┐
                                 │   AegisEnforcementNode    │  ◄── 2. In-Memory AST Delta Gate
                                 │  (Code Delta Compiler)    │      (EvaluationService + Baseline)
                                 └─────────────┬─────────────┘
                                               │
                                 ┌─────────────┴─────────────┐
                                 │   NativeAegisExecutor     │  ◄── 3. Sealed Tool Execution
                                 │  (Hardened I/O Interceptor)│     (Blocks Non-Compliant Disk Write)
                                 └─────────────┬─────────────┘
                                               │
                                               ▼
                                  FileSystem / Workspace Write
```

---

## 4. Phase-by-Phase Technical Blueprint

### Phase I: Domain Core Extraction (`aegis.core`)
- Pure Python domain logic with zero dependencies on agent orchestration frameworks.
- [registry.py](file:///c:/dev/projects/aegis/src/aegis/core/registry.py): `RegistryLoader` and Pydantic `Rule` policy definitions.
- [parser.py](file:///c:/dev/projects/aegis/src/aegis/core/parser.py): `TreeSitterAnalyzer` for in-memory AST delta evaluation.
- [baseline.py](file:///c:/dev/projects/aegis/src/aegis/core/baseline.py): `BaselineManager` for debt management.

### Phase II: Native Runtime Integration (`aegis.runtime`)
- [state.py](file:///c:/dev/projects/aegis/src/aegis/runtime/state.py): Defines `AegisState` extending `AgentState` with `governance_context`.
- [nodes.py](file:///c:/dev/projects/aegis/src/aegis/runtime/nodes.py): Implements `AegisPlanVerifier`, `AegisEnforcementNode`, and `AegisFinalGate`.
- [executor.py](file:///c:/dev/projects/aegis/src/aegis/runtime/executor.py): Implements `NativeAegisExecutor` to block non-compliant tool mutations.

### Phase III: The Self-Correction Loop (`aegis.domain`)
- [synthesizer.py](file:///c:/dev/projects/aegis/src/aegis/domain/synthesizer.py): Converts `ArchitecturalViolation` objects into structured LLM remediation prompts.

### Phase IV: Universal Agent Factory (`src/aegis/agent.py`)
- Single entry point `create_aegis_agent(model=None, tools=None, rules=None, workspace_root=".")`.

### Phase V: Platform Adapters (`aegis.adapters`)
- [deepagents.py](file:///c:/dev/projects/aegis/src/aegis/adapters/deepagents.py): `DeepAgentsAdapter`.
- [langgraph.py](file:///c:/dev/projects/aegis/src/aegis/adapters/langgraph.py): `LangGraphAdapter`.
- [mcp.py](file:///c:/dev/projects/aegis/src/aegis/adapters/mcp.py): `MCPAdapter` / FastMCP server (`AegisKernel`).

---

## 5. Architectural Guarantees & Status Verification Matrix

| Question | Verification Status | Rationale |
| :--- | :--- | :--- |
| **Is it "After-Build" compliance?** | **No** | It is **Correct-by-Construction** compliance. Intent, plans, and AST deltas are governed before disk write. |
| **Is it Native?** | **Yes** | Integrated as first-class nodes (`AegisPlanVerifier`, `AegisEnforcementNode`) in the execution graph. |
| **Is it Efficient?** | **Yes** | Microsecond-latency AST checks replace token-heavy LLM validation loops. |