# Aegis v3.0: Technical Architecture for Absolute Native Enforcement

**Date:** May 18, 2026
**Subject:** The Implementation of the Architectural Sandbox
**Objective:** Define the precise, end-to-end technical mechanisms required to guarantee that no agent can diverge from the Governance DNA.

---

## 1. The Core Paradigm Shift: From "Audit" to "Proxy"

In v2.0, Aegis operates in **Audit Mode**. The agent writes code to disk, and Aegis checks it. This allows drift to temporarily exist and requires the agent to willingly run the check.

In v3.0, Aegis operates in **Proxy Mode**. Aegis becomes the *file system* from the agent's perspective. Drift is mathematically impossible because the IO operation is intercepted and blocked.

---

## 2. Technical Design: The MCP Middleware Proxy

The guarantee of absolute enforcement relies on intercepting the standard MCP filesystem tools that agents use (e.g., `mcp_filesystem_write_file`, `mcp_filesystem_edit_file`).

### 2.1 The Interception Layer
Aegis will deploy a custom MCP Server that "shadows" the standard filesystem server. 

When the agent attempts an action:
1.  **Agent Request:** `call_tool(name="aegis_write_file", args={"path": "src/domain.py", "content": "import boto3"})`
2.  **Kernel Reception:** The `AegisKernel` receives the raw content payload.
3.  **Speculative V-FS (Virtual File System):** Aegis DOES NOT write to disk. It places the content into a high-speed, in-memory Virtual File System (V-FS).
4.  **In-Flight AST Scan:** The `EvaluationService` runs the `TREE_SITTER` and `SEMANTIC` engines against the V-FS blob.
5.  **The Governance Gate:**
    - If **PASS**: The Aegis Kernel executes the actual OS-level disk write. It returns a success message to the agent.
    - If **FAIL (Block)**: The disk write is aborted. The tool returns a `RemediationResult` directly as the tool's error output.

### 2.2 The "Hardened" Tool Schema
Agents will be provided with a modified toolset. Standard tools will be removed from their environment (via the `aegis install` bootstrapper), and replaced with:

- `aegis_read_file`: Returns file content *prepended* with the Governance DNA specific to that path (Ambient Context).
- `aegis_edit_file`: Performs speculative validation on the hunk before applying the patch.
- `aegis_write_file`: Performs full-file validation before writing.

---

## 3. End-to-End Native Enforcement Flow

How is this guaranteed across different tools (Claude, Aider, OpenDevin)?

### Step 1: The "Hostage" Bootstrapper (`uv run aegis install`)
The installer modifies the host environment's configuration (e.g., `claude_desktop_config.json`).
*   **Action**: It removes the default `mcp-filesystem` server.
*   **Action**: It injects the `aegis-kernel` server as the *exclusive* provider of filesystem operations for the target repository.
*   **Result**: The agent physically cannot read or write files without passing through the Aegis proxy.

### Step 2: Ambient DNA Injection
When the agent begins a task and calls `aegis_read_file(path="src/api.py")`, Aegis intercepts the read.
*   **Action**: Aegis queries the active rules for `src/api.py`.
*   **Result**: The tool returns:
    ```python
    # === AEGIS GOVERNANCE DNA ===
    # RULES ACTIVE: [strict-ood, no-db-in-api]
    # CAPABILITIES: [HTTP_ROUTING]
    # RESTRICTIONS: [DATABASE_ACCESS]
    # ============================
    
    from fastapi import APIRouter
    ...
    ```
    The agent's context window is seamlessly infused with the laws of that specific module.

### Step 3: Absolute Rejection
The agent attempts an unauthorized action: `aegis_edit_file(path="src/api.py", diff="...import psycopg2...")`.
*   **Action**: Aegis performs the in-flight AST scan and detects a `no-db-in-api` violation.
*   **Result**: The tool call throws a simulated `AegisArchitecturalException`. The agent receives a hard error:
    `TOOL_ERROR: Architectural Violation (HIGH). You attempted to import 'psycopg2' in an API layer. Write aborted. Refactor your plan to use the Repository interface.`

---

## 4. The Guarantee of Perfection

By moving from the **Application Layer** (checking code) to the **Transport Layer** (proxying the filesystem), Aegis achieves:

1.  **Zero Drift**: Bad code never touches the disk. The main branch is perfectly sterile.
2.  **Zero Opt-In**: The agent doesn't need to remember to run a check. The check *is* the write operation.
3.  **Zero Latency**: By evaluating in-memory before IO, we eliminate the costly write-evaluate-rewrite cycle.

### Architectural Decision
This is the ultimate evolution of Aegis. It transforms from a "Tool" into a **"Governance Runtime Environment" (GRE)**.
