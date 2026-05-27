# Aegis V4 "Architect-on-Demand" Enhancement Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surgically enhance Aegis V4 with an intuitive, on-demand "Skill" layer and a root-level `AEGIS.md` Scorecard for seamless agent onboarding.

**Architecture:** 
- **Scorecard Service**: Manages a Markdown facade of the project's health and rules.
- **Skill Wrappers**: High-level tools that orchestrate existing kernel services.
- **Project-Wide Scope**: All enhancements are strictly project-wide to maintain simplicity.

**Tech Stack:** Python 3.11+, MCP (Model Context Protocol).

---

## File Structure Changes

- Create: `src/aegis/domain/evaluation/scorecard.py` (New service for AEGIS.md management)
- Modify: `src/aegis/kernel/server.py` (Register new high-level tools)
- Modify: `src/aegis/infrastructure/installer.py` (Add AEGIS.md to default deployment)

---

### Task 1: Implement Scorecard Service

**Files:**
- Create: `src/aegis/domain/evaluation/scorecard.py`

- [ ] **Step 1: Create `ScorecardService`**

```python
class ScorecardService:
    def __init__(self, workspace_root: str):
        self.root = workspace_root
        self.path = os.path.join(workspace_root, "AEGIS.md")

    def generate(self, rules: list, violations: list, exceptions: list) -> str:
        # Calculate health score, list active rules, and pending suggestions.
        # Returns the full Markdown content.
        pass

    def sync_to_disk(self, content: str):
        # Write to AEGIS.md atomically.
        pass
```

---

### Task 2: High-Level "Discovery" Skill

**Files:**
- Modify: `src/aegis/kernel/server.py`

- [ ] **Step 1: Implement `discover_architectural_patterns`**

Wrap `_hypothesize_workspace_architecture` and format the output as "Proposed Laws" that can be accepted.

---

### Task 3: High-Level "Application" Skill

**Files:**
- Modify: `src/aegis/kernel/server.py`

- [ ] **Step 1: Implement `apply_governance_law`**

Create a tool that accepts a `law_id` or `pack_name` and automates the calling of `RulePackManager.install` or `evolve_ruleset(action='add_rule')`.

---

### Task 4: High-Level "Exception" Skill

**Files:**
- Modify: `src/aegis/kernel/server.py`

- [ ] **Step 1: Implement `request_exception`**

Create a tool that takes a `rule_id`, a `file_path`, and a `reason`. It should automatically update the `BaselineManager` and record the debt in the Scorecard.

---

### Task 5: Server Registration & Default Deployment

**Files:**
- Modify: `src/aegis/kernel/server.py`
- Modify: `src/aegis/infrastructure/installer.py`

- [ ] **Step 1: Register Tools**
Add the new tools to `AegisKernel._register_tools`.

- [ ] **Step 2: Update Scaffolding**
Ensure `AEGIS.md` is generated during `/aegis-init`.

---

## Verification Handoff

Plan complete. Saved to `docs/superpowers/plans/2026-05-27-aegis-architect-on-demand.md`.

**Execution options:**
1. **Subagent-Driven (recommended)**
2. **Inline Execution**

Which approach?
