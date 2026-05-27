# Aegis V4 Agent Coordination & Scaffolding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement cross-agent coordination memory and align workspace scaffolding with the universal harness system.

**Architecture:** 
- **Session Memory:** Introduce `SessionManager` to manage `.aegis/session.json`.
- **Handoff Logic:** Use the session memory to track task status and coordinate between different agents (Claude, Aider, Gemini).
- **Scaffolding Alignment:** Refactor `AegisKernel.scaffold_governance_framework` to use `AgentNativeInstaller` for multi-harness instruction deployment.

**Tech Stack:** Python 3.11+, Pydantic, Atomic file writes.

---

## File Structure Changes

- Create: `src/aegis/domain/evaluation/session.py` (Session state management)
- Modify: `src/aegis/kernel/server.py` (Update scaffolding and validation with session awareness)
- Modify: `src/aegis/cli/main.py` (Update CLI help for Gemini)
- Modify: `src/aegis/infrastructure/installer.py` (Expose harness detection)

---

### Task 1: Update CLI Help for Gemini

**Files:**
- Modify: `src/aegis/cli/main.py`

- [ ] **Step 1: Update `install` command help**

Change `--tool` help to include `gemini`.

```python
    def install(
        self,
        tool: str | None = typer.Option(
            None, "--tool", help="Target tool: claude, aider, gemini (omit for all)"
        ),
    ):
```

- [ ] **Step 2: Verify CLI help**

Run: `python -m aegis.cli.main install --help`

---

### Task 2: Implement Session Memory (`.aegis/session.json`)

**Files:**
- Create: `src/aegis/domain/evaluation/session.py`
- Test: `tests/test_session_manager.py`

- [ ] **Step 1: Define `SessionState` model and `SessionManager`**

```python
from pydantic import BaseModel, Field
from datetime import datetime
import json
import os

class SessionState(BaseModel):
    last_validation_time: datetime | None = None
    last_agent_id: str | None = None
    active_task: str | None = None
    handoff_notes: str | None = None

class SessionManager:
    def __init__(self, workspace_root: str):
        self.path = os.path.join(workspace_root, ".aegis", "session.json")

    def load(self) -> SessionState:
        if not os.path.exists(self.path):
            return SessionState()
        with open(self.path, "r") as f:
            return SessionState.model_validate_json(f.read())

    def save(self, state: SessionState):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            f.write(state.model_dump_json(indent=2))
```

- [ ] **Step 2: Write tests for session management**

Verify atomic save/load and default state.

---

### Task 3: Align Scaffolding with Universal Harnesses

**Files:**
- Modify: `src/aegis/kernel/server.py`

- [ ] **Step 1: Refactor `_generate_agents_md` to `_deploy_all_workspace_instructions`**

Instead of calling the legacy static method, instantiate `AgentNativeInstaller` and call `install(workspace_root=self.workspace_root)` which now handles all harnesses (Claude, Aider, Gemini).

- [ ] **Step 2: Update `scaffold_governance_framework`**

Call the new deployment method.

- [ ] **Step 3: Verify with integration test**

Verify that `aegis-init` now creates `.claude.md`, `AGENTS.md`, and `GEMINI.md`.

---

### Task 4: Agent Coordination in Validation Loop

**Files:**
- Modify: `src/aegis/kernel/server.py`

- [ ] **Step 1: Update `validate_architecture_compliance` to record session state**

Record the `last_validation_time` and potentially an `agent_id` (if we can detect it from environment variables like `CLAUDE_AGENT_ID` or similar).

- [ ] **Step 2: Add optional coordination notes**

Allow the agent to pass a `handoff_note` to the validation tool to store for the next agent.

---

## Verification Handoff

Plan complete. Saved to `docs/superpowers/plans/2026-05-27-aegis-coordination-alignment.md`.

**Execution options:**
1. **Subagent-Driven (recommended)**
2. **Inline Execution**

Which approach?
