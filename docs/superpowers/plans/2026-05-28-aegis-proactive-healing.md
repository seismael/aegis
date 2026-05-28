# Aegis V4 Phase 4: Proactive & Self-Healing Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Aegis from a reactive gatekeeper into a proactive, self-healing partner by implementing machine-readable remediations, interactive onboarding, and ambient context delivery.

**Architecture:** 
- **Diff-Based Remediation**: Upgrade the violation models to support machine-readable patches.
- **Conversational Onboarding**: Refactor `/aegis-init` into a discovery-and-negotiation dialogue.
- **Ambient Context**: Leverage MCP resources to push architectural laws to the agent's context window.

**Tech Stack:** Python 3.11+, MCP (Model Context Protocol), `difflib`.

---

## File Structure Changes

- Modify: `src/aegis/domain/evaluation/ports.py` (Add patch support to models)
- Modify: `src/aegis/domain/evaluation/service.py` (Generate diffs for remediations)
- Modify: `src/aegis/kernel/server.py` (Refine discovery and add context resources)
- Modify: `src/aegis/resources/skills/aegis-init.md` (Update skill instructions)

---

### Task 1: Machine-Readable Remediations (MCP Diff Support)

**Files:**
- Modify: `src/aegis/domain/evaluation/ports.py`
- Modify: `src/aegis/domain/evaluation/service.py`
- Test: `tests/test_remediation_diffs.py`

- [ ] **Step 1: Update `ArchitecturalViolation` model**
Add an optional `proposed_patch: str | None = None` field to the Pydantic model.

- [ ] **Step 2: Implement `DiffGenerator`**
Update the `EvaluationService` to generate a unified diff for simple regex or AST violations where a clear replacement is known.

- [ ] **Step 3: Update Kernel validation response**
Ensure the `validate_architecture_compliance` tool includes the raw diff in its output so agents can apply it using their native file-editing tools.

---

### Task 2: Interactive Discovery Loop (Refined Onboarding)

**Files:**
- Modify: `src/aegis/kernel/server.py`
- Modify: `src/aegis/resources/skills/aegis-init.md`

- [ ] **Step 1: Enhance `discover_architectural_patterns`**
Update the tool to return a structured JSON list of "Proposals" (e.g., `{"id": "hexagonal", "relevance": 0.9, "reason": "Detected /domain and /infra folders"}`).

- [ ] **Step 2: Refactor `/aegis-init` skill**
Update the markdown skill instructions to tell the agent to *negotiate* the architecture: "I see X, I propose Y. Shall we enable?"

---

### Task 3: Ambient Awareness (Architectural Context Resource)

**Files:**
- Modify: `src/aegis/kernel/server.py`

- [ ] **Step 1: Implement `aegis://architecture/context/{path}`**
Refine this resource to return a high-signal "Law Summary" for the specific module the agent is entering.

- [ ] **Step 2: Enable Subscription (Future-Proofing)**
Ensure the resource is registered such that client-side refreshes trigger an update notification if the `AEGIS.md` scorecard changes.

---

## Verification Handoff

Plan complete. Saved to `docs/superpowers/plans/2026-05-28-aegis-proactive-healing.md`.

**Execution options:**
1. **Subagent-Driven (recommended)**
2. **Inline Execution**

Which approach?
