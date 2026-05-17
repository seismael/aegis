# Aegis Universal Agentic Governance Protocol

This document establishes the mandatory architectural enforcement protocol for ALL agentic entities (Claude, Aider, OpenCode, Gemini, etc.) operating within this repository.

## 🛡️ The Governance Mandate
Architecture is an **active gate**, not a static document. Every code change MUST be validated against the project's structural invariants defined in `.aegis/rules.yaml`.

## 🤖 Agent Workflow (Universal)

### 1. Context Gathering
Before proposing or executing any structural change, you MUST:
- Read `SPEC.md` to understand the system topology.
- Read `.aegis/rules.yaml` to identify active logical constraints.

### 2. Pre-Correction Validation
Run the **`validate_architecture_compliance`** MCP tool (or execute `uv run aegis check --staged`) BEFORE finalizing any code modification.

### 3. Self-Remediation Loop
If violations are detected:
- Call the **`get_remediation_prompt`** tool for the specific violation ID.
- Use your internal reasoning to apply the refactor described in the prompt.
- Re-run the validation until the check passes.

### 4. Consensus Evolution
Agents are FORBIDDEN from modifying `.aegis/rules.yaml` or `SPEC.md` directly. All changes to the "Law" must be negotiated with the user.
- **Claude**: Use the `/aegis-evolve` skill.
- **Aider/Others**: Explicitly ask the user: "The current [Rule ID] blocks this change. Should we evolve the rule or refactor the code?"

## 🛠️ Tool-Specific Integration

### Claude Code
Aegis is integrated via skills in `.claude/skills/`. Use `/aegis-init` to start.

### Aider
Aegis is mapped via `.aider.conf.yml`. Ensure the `mcp-server` is active. Aider's "Architect Mode" natively respects this protocol.

### OpenCode / OpenDevin
The environment is bootstrapped with the Aegis headless check. Use `uv run aegis check` to verify your sandbox state before submitting.
