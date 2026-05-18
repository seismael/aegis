# Strategic Review: Aegis in the Agentic Era

## 1. The 'Legacy Tool' Anti-Pattern
Current state: Aegis acts as a high-fidelity **Linter**. 
- **Workflow**: Generate -> Check -> Fail -> Fix.
- **Problem**: This is a reactive legacy pattern. It burns tokens, increases latency, and treats the AI agent as a "junior coder" that needs correction.

## 2. The 'Agent-Native' Vision
Target state: Aegis acts as a **Structural Invariant Provider (Steering-First)**.
- **Workflow**: Fetch Laws -> Steer Generation -> Validate.
- **Benefit**: Zero-drift by design. The agent "knows" the architecture before the first line is written.

## 3. Critical Feedback & Identified Gaps

### A. Lack of 'Pre-emptive Discovery'
Agents currently only discover rules *after* a violation. 
*Fix*: Implement `get_relevant_rules(path)` so agents can query the "Law of the Land" before touching a module.

### B. High-Friction Initialization
The `/aegis-init` loop is too interrogative. Agents should be proactive.
*Fix*: Shift from "Agent asking Human" to "Agent proposing to Human" based on an initial codebase sweep.

### C. Context Fragmentation
The Model Context Protocol (MCP) is used for 'Tools' but underutilized for 'Prompts' and 'Resources'.
*Fix*: Make `aegis://rules` the primary context source that agents are instructed to read *first*.

## 4. Proposed Architectural Pivot: 'Steering-First Governance'

| Feature | Passive (Current) | Active (Target) |
|---|---|---|
| **Discovery** | Manual / CLI | Automatic via Context Injection |
| **Validation** | Post-generation | Real-time / Pre-generation |
| **Remediation** | Generic Error | RAG-Optimized Pathing |
| **Role** | Auditor | Principal Architect |

## 5. Next Steps
1.  **Enhance MCP Kernel**: Add proactive rule discovery tools.
2.  **Consolidate Skills**: Merge separate skill files into a unified 'Operational Protocol'.
3.  **Optimize Prompts**: Create 'Steering Prompts' that set the architectural stage at the beginning of a session.
