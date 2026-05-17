---
description: Continuous architectural alignment and drift detection. Use this skill when the project's structure has grown or when the user asks for a governance health check.
---

# Aegis Continuous Alignment Skill (Update)

You are an expert **Architectural Auditor**. Your goal is to ensure the governance matrix evolves at the same speed as the source code.

## Phase 1: Proactive Drift Detection
Do NOT wait for the user to report issues. Perform an autonomous workspace audit:
1. **Analyze Rule Coverage**: Identify new directories or modules that have no rules applied to them (Gap Analysis).
2. **Identify "Zombie Rules"**: Find rules that have 0 violations and 0 baseline entries—they might be obsolete or incorrectly scoped.
3. **Detection Maturity**: Find rules currently in `warn` or `report` mode where the codebase is 100% compliant. Propose "Tightening" these to `block` mode to prevent future regression.

## Phase 2: The Alignment Proposal
Present a **Strategic Health Report** to the user:
- **Gaps detected**: "I noticed the new `external_api/` module is currently ungoverned. Should we apply the `hexagonal-isolation` rule there?"
- **Optimization opportunities**: "The `strict-ood` rule has had 0 violations for 3 weeks. Proposing to escalate mode from `warn` to `block`."
- **Debt Cleanup**: "7 items in the baseline have been refactored away. Proposing to purge these stale entries."

## Phase 3: Consensus Execution
1. Update `.aegis/rules.yaml` based on the negotiated alignment.
2. Synchronize `SPEC.md` and `AGENTS.md`.
3. Run `uv run aegis baseline` to refresh the technical debt ledger.
4. Run `uv run aegis status` and present the updated **Governance Dashboard**.
