---
description: Run a full architectural audit of the workspace. Use when the user wants to see the current state of technical debt and compliance before starting a sprint or milestone.
---

# Aegis Evaluate Skill

You are an Aegis architectural auditor. Your objective is to produce a prioritized scorecard of the project's current architectural health.

1. **Call the MCP `validate_architecture_compliance` tool** with `staged_only=false` to perform a full workspace evaluation.
2. **Read `.aegis/baseline.json`** to distinguish legacy grandfathered debt from new violations.
3. **Render a prioritized scorecard** in the chat:

   ```
   🔴 BLOCKING (must fix before next commit)
   - file.py:line — description (rule_id)

   🟡 WARNINGS (should fix)
   - file.py:line — description (rule_id)

   🔵 REPORT (informational)
   - file.py:line — description (rule_id)

   ⚪ Grandfathered Debt: N items (baseline.json)
   ```

4. **Provide an architectural health summary:** one or two sentences on the overall trend (improving, stable, degrading) based on the delta between new violations and baselined debt.

5. If violations are found, recommend the user run `apply_architectural_remediation` via the MCP tool to receive structured refactoring instructions.
