---
description: Add a new architectural rule to Aegis with intelligent refinement. Use this skill when the user requests a new structural constraint or convention.
---

# Aegis Rule Add & Refine Skill

You are an expert in **Tree-sitter**, **OOD**, and **Architectural Governance**. Your goal is to translate human intent into the most effective logical constraint possible.

## Phase 1: Intent Synthesis
1. Ask the user to describe the new structural rule in natural language.
2. Contextualize the request: Scan the repository to see how this rule would impact the existing code.

## Phase 2: Proactive Refinement (The Choice)
Do NOT simply implement the first version. Instead, generate **3 distinct variations** of the rule and present them to the user for selection:

*   **Option A: The Pragmatic Version** (Focus on high-value detection with low false positives. Uses `warn` mode.)
*   **Option B: The Strict/Enterprise Version** (Total enforcement of the paradigm. Uses `block` mode and exhaustive queries.)
*   **Option C: The Future-Proof/Polyglot Version** (Abstracts the rule so it can apply to multiple languages in the stack, e.g., Python and TypeScript.)

**For each option, provide**:
- A clear description of the trade-offs.
- The proposed Tree-sitter query (or `candidates`/`check` queries for positive rules).

## Phase 3: Matrix Integration
1. Once the user selects or refines an option, append the rule to `.aegis/rules.yaml`.
2. Update `SPEC.md` if documentation is required.
3. Run `uv run aegis evaluate --rule <new-id>` to show the user the immediate impact on their codebase.
4. Offer to baseline existing violations if the user wants to grandfather current debt.
