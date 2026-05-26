# Aegis V4 Universal Harness & Semantic Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Aegis into a universal governance protocol by refactoring the installer for multi-harness support (including Gemini), hardening the semantic engine, and optimizing graph analysis performance.

**Architecture:** 
- **Universal Harness:** Move from hardcoded installer logic to a plugin-based `HarnessInterface` system.
- **Re-entrant Semantics:** Replace the heuristic PoC in `SemanticAnalyzer` with a robust rubric-handback system.
- **Incremental Graph:** Implement a persistent (disk-backed or memory-cached) adjacency graph to avoid full workspace scans on JIT calls.

**Tech Stack:** Python 3.11+, MCP (Model Context Protocol), Pydantic, structlog.

---

## File Structure Changes

- Create: `src/aegis/infrastructure/harnesses/base.py` (Abstract interface for AI harnesses)
- Create: `src/aegis/infrastructure/harnesses/claude.py` (Claude Code implementation)
- Create: `src/aegis/infrastructure/harnesses/aider.py` (Aider implementation)
- Create: `src/aegis/infrastructure/harnesses/gemini.py` (Gemini CLI implementation)
- Modify: `src/aegis/infrastructure/installer.py` (Entry point for multi-harness installation)
- Modify: `src/aegis/domain/evaluation/analyzers/semantic.py` (Hardening rubric logic)
- Modify: `src/aegis/domain/evaluation/analyzers/graph.py` (Adding adjacency caching)

---

### Task 1: Define Universal Harness Interface

**Files:**
- Create: `src/aegis/infrastructure/harnesses/base.py`
- Test: `tests/test_harness_architecture.py`

- [ ] **Step 1: Write the failing test for harness interface**

```python
import pytest
from aegis.infrastructure.harnesses.base import BaseHarness

def test_harness_interface_cannot_be_instantiated():
    with pytest.raises(TypeError):
        BaseHarness()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_harness_architecture.py`
Expected: FAIL (Module not found)

- [ ] **Step 3: Implement BaseHarness interface**

```python
from abc import ABC, abstractmethod
from pathlib import Path

class BaseHarness(ABC):
    def __init__(self, home: Path):
        self.home = home

    @abstractmethod
    def install(self) -> list[str]:
        """Inject Aegis into the harness global config. Returns list of error messages."""
        pass

    @abstractmethod
    def deploy_skills(self) -> list[str]:
        """Deploy markdown skills to the harness global registry."""
        pass

    @abstractmethod
    def deploy_workspace_instructions(self, workspace_root: str) -> list[str]:
        """Generate/update workspace-level instructions (GEMINI.md, .claude.md, etc.)"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_harness_architecture.py`
Expected: PASS

---

### Task 2: Migrate Claude & Aider to Harness Plugins

**Files:**
- Create: `src/aegis/infrastructure/harnesses/claude.py`
- Create: `src/aegis/infrastructure/harnesses/aider.py`
- Modify: `src/aegis/infrastructure/installer.py`

- [ ] **Step 1: Implement ClaudeHarness**

Extract logic from `AgentNativeInstaller._inject_claude` and `_deploy_claude_skills`. Add `deploy_workspace_instructions` to generate `.claude.md`.

- [ ] **Step 2: Implement AiderHarness**

Extract logic from `AgentNativeInstaller._inject_aider`. Add `deploy_workspace_instructions` to generate `AGENTS.md`.

- [ ] **Step 3: Refactor AgentNativeInstaller**

```python
from aegis.infrastructure.harnesses.claude import ClaudeHarness
from aegis.infrastructure.harnesses.aider import AiderHarness

class AgentNativeInstaller:
    def __init__(self):
        self.harnesses = {
            "claude": ClaudeHarness(Path.home()),
            "aider": AiderHarness(Path.home()),
        }

    def install(self, target: str | None = None, workspace_root: str | None = None):
        targets = [target] if target else self.harnesses.keys()
        for t in targets:
            h = self.harnesses.get(t)
            if h:
                h.install()
                h.deploy_skills()
                if workspace_root:
                    h.deploy_workspace_instructions(workspace_root)
```

- [ ] **Step 4: Verify migration with existing tests**

Run: `pytest tests/test_installer.py`

---

### Task 3: Implement Gemini CLI Harness

**Files:**
- Create: `src/aegis/infrastructure/harnesses/gemini.py`
- Modify: `src/aegis/infrastructure/installer.py`

- [ ] **Step 1: Write failing test for Gemini installation**

```python
def test_gemini_installer_mutates_config(tmp_path):
    config_file = tmp_path / ".gemini.json"
    harness = GeminiHarness(tmp_path)
    harness.install()
    assert config_file.exists()
    assert "aegis" in config_file.read_text()

def test_gemini_deploy_workspace_instructions(tmp_path):
    harness = GeminiHarness(tmp_path)
    harness.deploy_workspace_instructions(str(tmp_path))
    assert (tmp_path / "GEMINI.md").exists()
```

- [ ] **Step 2: Implement GeminiHarness**

Handle `~/.gemini.json` injection. Implement `deploy_workspace_instructions` to generate `GEMINI.md`.

- [ ] **Step 3: Update Installer Registry**

Add `GeminiHarness` to the `harnesses` dict in `AgentNativeInstaller`.

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_installer.py`

---

### Task 4: Hardening the Semantic Engine (Re-entrant Rubric)

**Files:**
- Modify: `src/aegis/domain/evaluation/analyzers/semantic.py`
- Modify: `src/aegis/kernel/server.py`

- [ ] **Step 1: Refactor `build_rubric` to be mandatory for semantic rules**

Ensure that if a semantic rule is encountered, Aegis returns a structured handback that *forces* the agent to evaluate and report back.

- [ ] **Step 2: Update `validate_architecture_compliance`**

Modify the server logic to detect if semantic rules are present and append the rubric to the violation report.

---

### Task 5: Performance - Incremental Graph Cache

**Files:**
- Modify: `src/aegis/domain/evaluation/analyzers/graph.py`

- [ ] **Step 1: Implement Adjacency Caching**

Modify `GraphAnalyzer.build_import_graph` to use a file-modification-time based cache. If files haven't changed since last scan, return the cached adjacency list.

---

## Verification Handoff

Plan complete. Saved to `docs/superpowers/plans/2026-05-27-aegis-universal-harness-semantic.md`.

**Execution options:**
1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks.
2. **Inline Execution** - Execute tasks in this session using executing-plans.

Which approach?
