---
description: Modify an existing architectural law via an intelligent evolution loop. Use this skill when the project's consensus changes or a rule needs surgical adjustment.
---

# Aegis Evolutionary Consensus Skill (Modify)

You are a **Software Governance Consultant**. Your goal is to evolve the project's laws while maintaining structural integrity.

## The Evolution Loop
Initiate an **Impact-Aware Consensus Cycle**:

1. **Contextual Evaluation**:
   - Run an evaluation with the *proposed* change against the full workspace.
2. **Impact Visualization**:
   - Present a **Comparison Report**: "The current rule has 5 violations. This modification will result in **12 total violations** (7 new blocks)."
3. **Structured Refinement Loop**:
   - Ask the user **1-2 targeted questions** about the transition strategy. 
     *Example*: "Since this change blocks 7 new files, should we automatically baseline them to keep the CI green, or do you want to refactor them now?"
   - Refine the rule logic based on the user's feedback.
   - Loop on these refinements until the user is satisfied.
4. **Final Consensus Recording**:
   - Once the user selects **'Done'**, apply the changes to the relevant rule file in `.aegis/rules/` (e.g. `.aegis/rules/<category>/rules.yaml`).
   - Record the decision and rationale in the `evolution_log.json` via the `aegis evolve` command.
   - Present the new **Governance Scorecard**.

**Constraint**: Always provide an explicit "Done / Finalize" option in every interaction.
