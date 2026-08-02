# Aegis V4: Agent-Native Technical Specification & Data Contracts

> **Canonical Technical Specification** for Aegis Native Engine & SDK based on [TEMP.md](file:///c:/dev/projects/aegis/TEMP.md).

---

## 1. Governance State & Data Contracts

### 1.1 `GovernanceContext` Schema

```python
class GovernanceContext(TypedDict):
    """Governance execution context audit trail."""
    is_clean: bool
    total_violations: int
    active_violations: list[dict[str, Any]]
    remediation_prompt: str | None
```

### 1.2 `AegisState` Schema

```python
class AegisState(TypedDict):
    """
    Governance-hardened AgentState schema for LangGraph StateGraph topologies.
    """
    messages: list[Any]
    pending_tool_call: dict[str, Any] | None
    governance_valid: bool
    governance: Annotated[list[GovernanceContext], operator.add]
```

---

## 2. Component API Contracts

### 2.1 Universal Agent Entry Point (`src/aegis/agent.py`)

```python
agent = create_aegis_agent(rules: list[Rule], workspace_root: str = ".")

# 1. Proactive Pre-Flight Plan Verification
plan_res = agent.verify_plan(proposed_imports: list[str], target_module: str)
# Returns: {"plan_valid": bool, "violations": list, "feedback": str}

# 2. In-Memory AST Delta Check
delta_res = agent.evaluate_code_delta(code_string: str, language: str, file_path: str)
# Returns: {"governance_valid": bool, "total_violations": int, "active_violations": list, "remediation_prompt": str}

# 3. Sealed Tool Execution
out = agent.execute_tool(tool_name: str, tool_args: dict[str, Any], tool_fn: Callable)
# Raises AegisGovernanceError if payload violates active rules
```

### 2.2 DeepAgents Ecosystem Adapter (`aegis.adapters.deepagents`)

```python
adapter = DeepAgentsAdapter(workspace_root=".")

loop_res = adapter.run_governed_agent_loop(
    initial_request="Implement billing service",
    code_generator_fn=llm_generator_fn,
    tool_fn=write_file_tool,
    max_retries=3
)
# Returns: {"success": bool, "attempts": int, "output": Any, "history": list}
```

### 2.3 LangGraph Ecosystem Adapter (`aegis.adapters.langgraph`)

```python
adapter = LangGraphAdapter(rules=rules, workspace_root=".")
graph_update = adapter.run_step(state: AegisState, tool_fn: Callable | None = None)
```

---

## 3. Microkernel Tool Surface (FastMCP)

| MCP Tool | Function Signature | Description |
| :--- | :--- | :--- |
| `check_architecture` | `check_architecture(modified_files: list[str])` | Evaluates active workspace files against governance rules. |
| `plan_architecture` | `plan_architecture(intent: str, file_path: str)` | Pre-flight intent check returning JIT scoped rules. |
| `init_governance` | `init_governance(workspace_root: str)` | Scaffolds `.aegis/rules`, `pyproject.toml`, `AGENTS.md`. |
| `query_graph` | `query_graph(source_module: str)` | Returns dependency coupling and adjacency lists. |

---

## 4. Multi-Engine Evaluation Pipeline

1. **Tree-sitter AST Engine**: In-memory structural node analysis for Python, TypeScript, JavaScript, Rust.
2. **Import Graph Engine**: $O(1)$ workspace dependency analysis and layer isolation.
3. **Regex Engine**: Pattern matching for credentials, `print(` statements, and style invariants.
4. **Semantic Engine**: Re-entrant LLM self-grading for natural language design rubrics.
