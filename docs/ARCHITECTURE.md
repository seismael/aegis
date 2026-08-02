# Aegis V4 Architecture: Agent-Native Governance SDK & Microkernel

> **Canonical Architectural Blueprint** based on [TEMP.md](file:///c:/dev/projects/aegis/TEMP.md).

---

## 1. Core Vision & Paradigm Shift

Aegis is an **Agent-Native Architectural Runtime Engine & Governance SDK** designed to govern AI code generation in real-time. Instead of acting as a post-hoc scanner or external CI check, Aegis embeds directly into agent execution graphs (DeepAgents, LangGraph, Claude Code, Aider, Gemini CLI).

### The "Correct-by-Construction" Model

```text
                                  Agent Intent / User Request
                                               │
                                               ▼
                                 ┌───────────────────────────┐
                                 │   AegisPlanVerifier       │  ◄── 1. Proactive Pre-Flight Plan Gate
                                 │  (Plan / Intent Check)    │      (Halts token waste before code gen)
                                 └─────────────┬─────────────┘
                                               │
                                 ┌─────────────┴─────────────┐
                                 │   Plan Approved / Valid   │
                                 └─────────────┬─────────────┘
                                               │
                                               ▼
                                 ┌───────────────────────────┐
                                 │   AegisEnforcementNode    │  ◄── 2. In-Memory AST Delta Gate
                                 │  (Code Delta Compiler)    │      (Microsecond Tree-sitter check)
                                 └─────────────┬─────────────┘
                                               │
                                 ┌─────────────┴─────────────┐
                                 │   NativeAegisExecutor     │  ◄── 3. Sealed Tool Execution
                                 │  (Hardened I/O Interceptor)│     (Blocks Non-Compliant Disk Write)
                                 └─────────────┬─────────────┘
                                               │
                                               ▼
                                 ┌───────────────────────────┐
                                 │      AegisKernel          │  ◄── 4. Microkernel Compliance Gate
                                 │ (FastMCP check_arch)      │      (Final JIT workspace certification)
                                 └───────────────────────────┘
```

---

## 2. Modular SDK Package Taxonomy

```text
/src/aegis/
├── agent.py            # Unified Entry Point (create_aegis_agent)
├── core/               # Pure Framework-Agnostic Core
│   ├── registry.py     # Pydantic Policy Registry Loader (RegistryLoader)
│   ├── parser.py       # Pure AST-Delta Compiler (TreeSitterAnalyzer)
│   ├── baseline.py     # Debt Ledger Manager (BaselineManager)
│   └── scoping.py      # Path Component Scope Filter (ScopeFilter)
├── runtime/            # Agentic Runtime Glue
│   ├── state.py        # AegisState & GovernanceContext schemas
│   ├── nodes.py        # AegisPlanVerifier, AegisEnforcementNode, AegisFinalGate
│   ├── executor.py     # NativeAegisExecutor (Sealed Tool Interceptor)
│   └── wrappers.py     # aegis_hardened_tool decorator
├── domain/             # Domain Intelligence & Refinement Loop
│   ├── synthesizer.py  # RemediationPromptSynthesizer (Self-Correction Loop)
│   ├── evaluation_service.py # EvaluationService Coordinator
│   ├── scorecard.py    # Scorecard Dashboard Generator
│   └── telemetry.py    # Local Telemetry Recorder
└── adapters/           # Ecosystem & Platform Adapters
    ├── deepagents.py   # DeepAgentsAdapter & create_deepagents_governed_agent
    ├── langgraph.py    # LangGraphAdapter & GovernedExecutionGraph
    └── mcp.py          # FastMCP Microkernel Adapter (AegisKernel)
```

---

## 3. Layered Component Responsibilities

### 3.1 Pure Core Engine (`aegis.core`)
- **Policy Registry Loader**: Loads declarative YAML rules into Pydantic models.
- **Tree-sitter AST Compiler**: In-memory structural delta analyzer.
- **Baseline Manager**: Manages grandfathered technical debt ledgers in `.aegis/baseline.json`.
- **Scope Filter**: Component-boundary path matcher (`src/domain/**`).

### 3.2 Native Runtime Glue (`aegis.runtime`)
- **`AegisPlanVerifier`**: Proactively verifies intent (proposed imports & target modules) before LLM code generation starts.
- **`AegisEnforcementNode`**: Evaluates in-memory AST deltas and implements `__call__(state)` for LangGraph StateGraph execution.
- **`NativeAegisExecutor`**: Intercepts tool execution calls (`write_file`, `edit_file`) and raises `AegisGovernanceError` on non-compliant payloads.

### 3.3 Domain Intelligence (`aegis.domain`)
- **`RemediationPromptSynthesizer`**: Converts raw mathematical violations into structured LLM self-correction prompts.
- **`EvaluationService`**: Coordinates multi-engine analyzers (AST, Graph, Regex, Semantic).

### 3.4 Ecosystem Adapters (`aegis.adapters`)
- **`DeepAgentsAdapter`**: Wraps DeepAgents / LangChain execution loops with self-correction prompt synthesis.
- **`LangGraphAdapter`**: Connects Aegis state updates into native LangGraph StateGraph topologies.
- **`MCPAdapter` (`AegisKernel`)**: Exposes FastMCP microkernel tools (`check_architecture`, `plan_architecture`).

---

## 4. Key Architectural Guarantees

1. **~90% LLM Token Tax Savings**: Intercepting non-compliant planning intent at `AegisPlanVerifier` stops invalid code generation loops before they begin.
2. **Microsecond Latency**: Pure in-process Python and Tree-sitter AST parsing replace expensive LLM validation calls.
3. **Zero Upgrade Drift**: Clean dependency-based integration via `AegisAgent` factory and adapters without framework hard-forking.
