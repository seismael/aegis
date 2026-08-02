# Aegis V4 — Universal Agent-Native Architectural Runtime Engine & SDK

[![PyPI Version](https://img.shields.io/pypi/v/aegis.svg)](https://pypi.org/project/aegis/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

**Aegis** is an **Agent-Native Architectural Runtime Engine & Governance SDK** that transforms software governance from a reactive post-hoc scan into a **Proactive, Correct-by-Construction Execution Primitive**.

Integrated natively into agent execution loops (DeepAgents, LangGraph, Claude Code, Aider, Gemini CLI), Aegis intercepts agent intent, evaluates in-memory AST deltas in microseconds, and seals disk tools—improving token efficiency and eliminating retry loops when agents introduce architectural drift.

---

## ⚡ Token Efficiency & Cost Analysis

Real agent trials (Claude Code, Gemini CLI) performing cross-layer DDD feature addition with 68 governance rules. Results are **agent-dependent**:

| Agent | Model | WITH Aegis | WITHOUT Aegis | Delta |
| :--- | :--- | :--- | :--- | :--- |
| Gemini CLI | gemini-3.5-flash | 390,544 input | 605,825 input | **+35.5% savings** |
| Claude Code | deepseek-v4-pro | 126,116 total | 98,092 total | -28.6% overhead |
| OpenCode | deepseek-v4-pro | AGENTS.md alone (no MCP) has zero effect | — | — |

Aegis is a **governance engine** first. Token efficiency is a secondary effect that varies by agent and model. The engine detects 133 violations across 25 files in 0.32s with 68 rules.

> For detailed methodology and complete trial data, see [Token Efficiency & Cost Analysis](file:///c:/dev/projects/aegis/docs/TOKEN_EFFICIENCY.md).

---

## 🏗️ Target Modular SDK Architecture

```text
/src/aegis/
├── __init__.py         # Top-Level SDK Exports (AegisAgent, AegisKernel, Rule)
├── agent.py            # Unified Factory Entry Point (create_aegis_agent)
├── core/               # Pure Framework-Agnostic Engine
│   ├── registry.py     # Pydantic Policy Registry Loader (RegistryLoader)
│   ├── parser.py       # Pure AST-Delta Compiler (TreeSitterAnalyzer)
│   ├── baseline.py     # Grandfathered Debt Ledger Manager (BaselineManager)
│   └── scoping.py      # Component-Boundary Scope Filter (ScopeFilter)
├── runtime/            # Agentic Runtime Glue
│   ├── state.py        # AegisState & GovernanceContext schemas
│   ├── nodes.py        # AegisPlanVerifier, AegisEnforcementNode, AegisFinalGate
│   ├── executor.py     # NativeAegisExecutor (Sealed Tool Interceptor)
│   └── wrappers.py     # aegis_hardened_tool decorator
├── domain/             # Domain Intelligence & Refinement Loop
│   ├── synthesizer.py  # RemediationPromptSynthesizer (Self-Correction Loop)
│   ├── evaluation_service.py # EvaluationService Multi-Analyzer Coordinator
│   ├── scorecard.py    # Scorecard Dashboard Generator
│   └── telemetry.py    # Local Telemetry Recorder
└── adapters/           # Ecosystem & Platform Adapters
    ├── deepagents.py   # DeepAgentsAdapter & create_deepagents_governed_agent
    ├── langgraph.py    # LangGraphAdapter & GovernedExecutionGraph
    └── mcp.py          # FastMCP Microkernel Adapter (AegisKernel)
```

---

## 🔄 The 4-Stage Native Execution Pipeline

```
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

## 💻 Quick Start & Usage

### Installation & Workspace Initialization

```bash
pip install aegis

# Initialize Aegis in your workspace (scaffolds .aegis/rules, pyproject.toml, AGENTS.md)
aegis init
```

---

### Using Aegis with DeepAgents (`DeepAgentsAdapter`)

```python
from aegis.adapters.deepagents import create_deepagents_governed_agent

# 1. Instantiate governed native agent
agent = create_deepagents_governed_agent(workspace_root=".")

# 2. Run governed self-correction execution loop
result = agent.run_governed_agent_loop(
    initial_request="Build billing service in src/domain/billing.py",
    code_generator_fn=deepagents_llm_generator,
    tool_fn=write_file_tool,
    max_retries=3,
)

print(f"Success: {result['success']}, Attempts: {result['attempts']}")
```

---

### Using Aegis with LangGraph (`LangGraphAdapter`)

```python
from aegis.adapters.langgraph import LangGraphAdapter

# Initialize LangGraph adapter for StateGraph execution
adapter = LangGraphAdapter(rules=rules, workspace_root=".")

# Execute governed state graph step
state = {
    "pending_tool_call": {
        "name": "write_file",
        "path": "src/domain/user.py",
        "content": "class User:\n    pass\n",
    }
}
update = adapter.run_step(state, tool_fn=write_file_tool)
print(f"Governance Valid: {update['governance_valid']}")
```

---

### Proactive Pre-Flight Plan Check via CLI

```bash
# Proactively verify architectural intent before generating code
aegis agent --workspace . --plan-import aegis.infrastructure --target-module aegis.domain.service
```

---

## 🛠️ MCP Microkernel Tools

When running as an MCP server (`aegis run`), Aegis provides a stateless microkernel for AI agents:

| Tool | Purpose |
| :--- | :--- |
| `check_architecture` | **The Gate.** In-process AST & dependency compliance check before completion. |
| `plan_architecture` | **The Blueprint.** Pre-flight validation of cross-cutting architectural modifications. |
| `init_governance` | **The Bootstrapper.** Scaffolds `.aegis/` framework and native instructions. |
| `find_patterns` | **The Scout.** Proactive pattern detection and rule proposals. |
| `apply_rules` | **The Architect.** Adopts rule packs or custom architectural intents. |
| `fetch_rubric` | **The Brain.** Re-entrant LLM self-grading for design intents. |
| `manage_rules` | **The Editor.** Evolve, add, or suppress active governance rules. |
| `query_graph` | **The Map.** $O(1)$ adjacency queries to analyze module boundaries. |
| `get_scorecard` | **The Dashboard.** Updates `.aegis/AEGIS.md` scorecard. |

---

## 📦 Battle-Tested Polyglot Rule Packs

Aegis includes 18+ pre-configured rule packs across multiple languages:
- **Architecture**: Domain-Driven Design (DDD), Hexagonal Architecture, Layer Isolation.
- **Security**: PII Detection, Credential Protection, Injection Defense.
- **Performance**: N+1 Query Interception, Memory Leak Audit.
- **Languages**: Native Tree-sitter AST support for **Python**, **TypeScript**, **JavaScript**, and **Rust**.

---

## 📄 License

[MIT License](LICENSE) — Aegis Governance Team
