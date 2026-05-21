# Aegis v3.0: Detailed Implementation Specification

**Date:** May 18, 2026
**Version:** 3.0-DRAFT (Absolute Native Enforcement)
**Status:** Strategic Blueprint

This document provides exhaustive technical details for the implementation of the Aegis v3.0 **Architectural Sandbox**. It covers the low-level mechanics of tool proxying, speculative validation, and the environment-level configuration shifts required to guarantee absolute architectural integrity.

---

## 1. System Topology: The Enforcement Middleware

```text
[ AI AGENT ] <--- JSON-RPC (MCP) ---> [ AEGIS MIDDLEWARE ] <--- Local IO ---> [ FILE SYSTEM ]
     ^                                         |
     |                                [ SPECULATIVE V-FS ]
     |                                         |
     +-------------------------------- [ ENFORCEMENT ENGINE ] (Tree-sitter/Semantic)
```

In v3.0, the Aegis Kernel acts as an **I/O Gateway**. The agent is physically isolated from the host file system.

---

## 2. Low-Level Component: The Speculative V-FS

To validate changes *before* they are written, Aegis implements an in-memory **Virtual File System (V-FS)**.

### 2.1 Implementation Detail (Pseudocode)
```python
class SpeculativeVFS:
    def __init__(self, real_root: str):
        self.real_root = real_root
        self.overlay: dict[str, str] = {} # path -> in-memory content

    def stage_change(self, path: str, new_content: str):
        """Prepare a change for validation."""
        self.overlay[path] = new_content

    def read(self, path: str) -> str:
        """Read from overlay if exists, otherwise from disk."""
        if path in self.overlay:
            return self.overlay[path]
        return read_real_disk(path)

    def commit(self, path: str):
        """Actually write the valid code to the real disk."""
        if path in self.overlay:
            write_real_disk(path, self.overlay[path])
            del self.overlay[path]
```

---

## 3. Tool Proxy Mechanics: The Interceptor Loop

Aegis v3.0 redefines the standard filesystem tools. Here is the exact logic for the `aegis_write_file` tool:

### 3.1 `aegis_write_file` Algorithm
1.  **Receive** `path` and `content` from the agent tool call.
2.  **Initialize** `SpeculativeVFS`.
3.  **Inject** `content` into the V-FS overlay.
4.  **Execute** `EvaluationService.evaluate_file(path, vfs_content)`.
    - Note: The analyzer must be updated to accept content strings or a VFS provider rather than just file paths.
5.  **Evaluate Severity**:
    - If violations contain `severity=HIGH` or `mode=BLOCK`:
        - **ABORT**: Do not call `vfs.commit()`.
        - **RETURN**: `MCP_ERROR` with structured `RemediationResult`.
    - If violations are `WARN` or `REPORT`:
        - **PROCEED**: Call `vfs.commit()`.
        - **RETURN**: `SUCCESS` but append the warnings to the tool's stdout for agent awareness.
6.  **Success**: Return `SUCCESS` status to the agent.

---

## 4. The "Hostage" Bootstrapper: Native Integration

To guarantee that the agent uses these proxies, the `AegisInstaller` must perform environment-level redirection.

### 4.1 Claude Desktop Integration
Modify `~/.claude/claude_desktop_config.json`:
- **Step A**: Locate the `mcpServers` entry for the standard `filesystem` server.
- **Step B**: **Disable or Remove** the standard entry.
- **Step C**: Inject the `aegis-kernel` with a new capability flag: `--mode enforced-sandbox`.
- **Step D**: Inject **Operational Invariants** into the agent's system prompt (using the `instructions` field in MCP).

### 4.2 Aider / CLI Integration
- Generate an `.aider.conf.yml` that overrides the default read/write commands with Aegis CLI wrappers.
- The wrapper should return a non-zero exit code on architectural violations, causing Aider's internal loop to retry the generation automatically.

---

## 5. Ambient DNA: Pre-emptive Context Injection

The `aegis_read_file` tool is a critical part of the steering mechanism. It ensures the agent never operates in a vacuum.

### 5.1 DNA Header Format
Every time an agent reads a file, Aegis injects the following header (in-memory only, not saved to disk):
```python
"""
AEGIS-GOVERNANCE-DNA
--------------------
CONTEXT: [Domain Layer]
ACTIVE-LAWS:
  - no-direct-db: "Database calls must go through Ports."
  - strict-ood: "Use interfaces for all dependencies."
CAPABILITIES: [BUSINESS_LOGIC, UNIT_TESTING]
RESTRICTIONS: [I/O, THIRD_PARTY_SDKs]
--------------------
"""
```
This forces the LLM to attend to these constraints in every attention head of its transformer block.

---

## 6. Safety & Resilience (The "Human Bypass")

Aegis must distinguish between a **Human** and an **Agent**.

- **Detection**: Use the MCP `client_info` or a unique `AEGIS_AGENT_TOKEN` injected by the bootstrapper.
- **Fail-Safe**: If Aegis detects it is interacting with a **Human** (manual CLI usage), it degrades to **Warn-only**.
- **Agent Lockdown**: If it is an **Agent**, the sandbox is **Strict**. There is no bypass for an autonomous system.

---

## 7. Performance Requirements

Absolute enforcement adds a validation step to every I/O operation. To maintain UX fluidly:
- **Hunk-Aware AST**: Only scan the modified nodes in the Tree-sitter tree.
- **Caching**: Store hashes of pass/fail semantic evaluations in a local SQLite cache.
- **Parallelism**: Run AST and Regex scans in parallel during the tool interception phase.

---

## 8. Engineering Standards: The Clean Code Implementation

To ensure Aegis remains the gold standard of architectural tools, the v3 implementation must follow these rigid software engineering principles:

### 8.1 Pure Domain Logic (Hexagonal)
- The **Speculative V-FS** and **Enforcement Interceptors** must be defined as pure domain services.
- They must depend on **Ports (Interfaces)** for actual disk I/O, allowing the entire sandbox to be tested in-memory without a physical filesystem.

### 8.2 Dependency Injection (IoC)
- The `SpeculativeVFS` must be injected into the `AegisKernel` at runtime.
- Use a **Provider Pattern** to swap between `RealFSProvider` (for humans) and `SpeculativeVFSProvider` (for agents).

### 8.3 Invariant Immutability
- Once the **Governance DNA** is loaded for a session, it must be treated as immutable. Rule modifications during an active sandbox session must trigger a **Session Reset** to prevent state leaks.

---

## 9. Comprehensive Testing Strategy

Absolute enforcement requires an absolute guarantee of correctness. The v3 suite will use a three-tier testing model:

### Tier 1: V-FS Unit Tests (Isolation)
- **Overlay Integrity**: Verify that staging a change in V-FS does not modify the real disk until `commit()` is called.
- **Read-Through Correctness**: Verify that V-FS correctly merges disk state with in-memory overlays.
- **Atomic Commits**: Verify that failures during `vfs.commit()` do not leave the file system in a corrupted state.

### Tier 2: Interceptor Integration Tests (The Proxy)
- **Speculative Bypass**: Test that `aegis_write_file` correctly routes to the `EvaluationService` before I/O.
- **Rejection Gating**: Verify that a simulated `HIGH` severity violation physically blocks the write operation.
- **Warning Passthrough**: Verify that `LOW/MEDIUM` violations allow the write but surface the metadata to the agent.

### Tier 3: Sandbox End-to-End Verification (The Jail)
- **Agent Simulation**: Use a mock AI agent to attempt to write "forbidden" code.
- **Configuration Hijacking**: Verify that the `AegisInstaller` correctly redirects standard MCP filesystem calls to the Aegis Kernel in a temporary environment.
- **Ambient Awareness**: Assert that the agent's context window contains the injected DNA header after a read operation.

---

## 10. Verification Checklist for Initial Release

| Component | Requirement | Verification Method |
|---|---|---|
| **V-FS** | In-memory overlay performance < 5ms | Benchmarked Unit Test |
| **Proxy** | Absolute block on `strict-ood` violation | Integration Test Suite |
| **DNA** | Validates against a 50k token context window | LLM-in-the-loop Test |
| **Installer** | Zero manual steps for Claude Desktop integration | E2E Mock Install |

---

## 11. Conclusion

V3.0 represents the **Total Colonization** of the agentic workflow. Aegis becomes the provider of truth for the codebase, ensuring that the project's architecture is not just a document, but a **Physical Law of the Sandbox**.
