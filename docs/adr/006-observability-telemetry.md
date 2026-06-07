# ADR 006: Agentic Observability and Telemetry

## Status
Accepted

## Context
As AI agents operate autonomously to implement features, engineering managers and human developers need visibility into how well the AI is respecting the architecture. Simply blocking the AI on violations is not enough; we need to measure the *health trajectory* of the repository and identify if agents are consistently struggling with specific architectural concepts.

## Decision
We built an **Agentic Observability** layer utilizing a Telemetry Recorder.

1. **Silent Tracking**: Every time the `check_architecture` tool is invoked, the results (passes, failures, specific rule violations) are appended to a `.aegis/telemetry.json` log.
2. **Health Scorecard**: We implemented a `get_scorecard` MCP tool that analyzes this telemetry data to produce a high-level summary of the repository's architectural health over time.
3. **Feedback Loop**: This allows the human operator to see patterns (e.g., "The AI agent has failed the Domain Isolation rule 14 times this week") and adjust the agent prompts or rule definitions accordingly.

## Consequences
- **Pros**: Provides quantitative metrics on AI performance. Allows organizations to trust autonomous agents by verifying their long-term compliance trajectory.
- **Cons**: The telemetry JSON file can grow large over time if not rotated or compacted.
