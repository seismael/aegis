# Aegis V4 Governance: Universal Agent-Native Protocol

You are governed by the **Aegis Architectural Microkernel**. This workspace uses **Agent-Native Governance** to ensure structural integrity and architectural alignment.

---

## 🛡️ Mandatory Compliance Protocol

Before declaring ANY coding task complete, you MUST follow this loop:

1.  **Validate**: Call `validate_architecture_compliance` with the list of modified files.
2.  **Remediate**: 
    - If **Structural Violations** are returned, apply the provided remediations natively.
    - If a **Semantic Rubric** is returned, use your reasoning to grade the code and fix any found intent-level drift.
3.  **Handoff**: If multiple agents are working in this workspace, check the **Coordination Info** in the validation response for handoff notes.
4.  **Repeat**: Re-run validation until **SUCCESS** is returned.

---

## 🛠️ Tooling & Expert Skills

### Core MCP Tools

| Tool | When to Use |
|------|-------------|
| `validate_architecture_compliance` | **Mandatory.** Call before task completion. |
| `plan_architecture` | Call before editing a file to get JIT rule context. |
| `request_semantic_grading_rubric` | For domain language or high-level design intent checks. |
| `scaffold_governance_framework` | For initial project setup or adding new rule packs. |
| `query_knowledge_graph` | To visualize dependencies or health-check a module. |
| `evolve_ruleset` | To add project-specific rules or suppress legacy debt. |

### Expert Personas (Skills)

Invoke these personas to help you manage the architecture:

- `/aegis-principal-architect` — Your default mindset. Load this to steer the project.
- `/aegis-init` — Bootstrap governance in a new project (discovery + scaffold).
- `/aegis-architect` — Translate requirements into new architectural laws.
- `/aegis-semantic-check` — Deep semantic self-grading for specific files.

---

## 🧠 Memory & Coordination

Aegis uses **Cross-Agent Memory** (`.aegis/session.json`) to track:
- **Last Validation**: Who checked the code and when.
- **Active Tasks**: What is currently being worked on.
- **Handoff Notes**: Technical context shared between agents.

**Note**: You can pass `handoff_note` during validation to share context with future agents.

---

## 🚫 Governance Invariants

- Do **NOT** disable or bypass Aegis governance.
- Do **NOT** manually edit `.aegis/baseline.json` (use `evolve_ruleset`).
- **Protocol-First**: Every task must be verified. No exceptions.
