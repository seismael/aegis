# Gemini Workspace Instructions: Aegis Governance

This workspace is governed by the **Aegis Architectural Microkernel**. To maintain high architectural standards, you must adhere to the **Agent-Native Governance Protocol**.

---

## 🚀 Native Integration with Gemini

As a Gemini agent, you are equipped with the **Aegis MCP Server**. You should use the following tools natively during your workflow:

### 1. Mandatory Validation
Before finishing any task, you **MUST** call:
> `validate_architecture_compliance(files_modified=[...])`

If violations are found, fix them and re-run.

### 2. Intent-Based Grading
If the validation tool returns a **Semantic Rubric**, you must:
- Read the rubric carefully.
- Use your reasoning powers to grade the code.
- Report and fix any intent-level violations.

---

## 🤝 Coordination with Other Agents

This workspace might be shared with other agents (Claude, Aider). Check the **Coordination Info** returned by the validation tool for:
- **Handoff Notes**: Technical context left by previous agents.
- **Last Active Agent**: Know who was working here before you.

You can leave your own notes by passing `handoff_note` to the validation tool.

---

## 🛠️ Key Resources

- **`AGENTS.md`**: The full project governance protocol.
- **`.aegis/rules/`**: The active architectural laws for this repo.
- **`SPEC.md`**: The technical specification you are building against.

**Invariant**: Do not declare a task complete until `validate_architecture_compliance` returns **SUCCESS**.
