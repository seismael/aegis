"""
Aegis Prompt Enricher — Injects scoped architectural rules into LLM prompts.

Before: Agent codes blindly, may violate rules, needs retry rounds.
After:  Agent sees rules in prompt, codes compliantly on first pass.

This is the proven +64-79% token savings mechanism from corrected.py,
productionized as a reusable Aegis component.
"""

from aegis.core.registry import Rule
from aegis.core.scoping import ScopeFilter
from aegis.domain.policy.parser import PolicyParser


def enrich_prompt(
    task: str,
    files: list[str],
    workspace: str = ".",
    max_rules: int = 20,
    tier: str = "core",
) -> str:
    """
    Enrich a coding task prompt with scoped architectural rules.

    Args:
        task: The user's coding task description.
        files: File paths the agent will modify (e.g. ["domain/services.py"]).
        workspace: Path to the project root (must have .aegis/rules/).
        max_rules: Maximum number of rules to include in the prompt.
        tier: Rule tier filter ("core" | "extended"). Ignored in this version
              since PolicyParser loads all installed rules regardless of tier.

    Returns:
        Enriched prompt string with rules prepended, ready for copy-paste
        or injection into an agent prompt pipeline.

    Raises:
        ValueError: If no rules are loaded from the workspace.
    """
    parser = PolicyParser(workspace)
    rules = parser.parse_all()
    if not rules:
        raise ValueError(
            f"No rules found in {workspace}. Run 'aegis init --tool claude' first."
        )

    relevant = ScopeFilter.filter_rules_for_files(files, rules, max_rules=max_rules)
    if not relevant:
        return task

    rules_text = _format_rules(relevant)
    return (
        f"Architectural rules for the files being modified:\n\n"
        f"{rules_text}\n\n"
        f"Follow ALL of these rules in your implementation.\n\n"
        f"Task: {task}"
    )


def enrich_prompt_minimal(
    task: str,
    files: list[str],
    workspace: str = ".",
) -> str:
    """
    Minimal version — returns the prompt unchanged if no rules apply.
    Useful for integration where rules may or may not be installed.
    """
    try:
        return enrich_prompt(task, files, workspace)
    except ValueError:
        return task


def _format_rules(rules: list[Rule]) -> str:
    """
    Format a list of Rule objects into human-readable prompt text.
    Each rule includes its ID, severity, description, and rationale.
    """
    lines = []
    for r in rules:
        lines.append(f"  {r.id} [{r.severity.value}]: {r.description}")
        if r.rationale:
            lines.append(f"    Rationale: {r.rationale}")
        if r.engine_type:
            lines.append(f"    Engine: {r.engine_type.value}")
    return "\n".join(lines)


__all__ = ["enrich_prompt", "enrich_prompt_minimal"]
