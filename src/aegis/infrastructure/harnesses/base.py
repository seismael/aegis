from abc import ABC, abstractmethod
from pathlib import Path

AEGIS_GOVERNANCE_DIRECTIVE = (
    "CRITICAL GOVERNANCE DIRECTIVE: "
    "You are governed by the Aegis Microkernel. "
    "Before declaring ANY coding task complete, you MUST execute the "
    "`validate_architecture_compliance` MCP tool. If it returns violations, "
    "you MUST remediate the code natively before proceeding."
)

AEGIS_SKILL_FILES = [
    "aegis-init.md",
    "aegis-principal-architect.md",
    "aegis-architect.md",
    "aegis-semantic-check.md",
]

AGENTS_TEMPLATE = """# Aegis V4 Governance

You are governed by the Aegis Architectural Microkernel.

## Mandatory Protocol

Before declaring ANY coding task complete, you MUST:

1. Call `validate_architecture_compliance` with the list of modified files.
2. If violations are returned, remediate the code natively.
3. Re-run validation until SUCCESS is returned.

## Available MCP Tools

| Tool | When to Use |
|------|-------------|
| `validate_architecture_compliance` | Before every task completion |
| `plan_architecture` | Before editing a file |
| `request_semantic_grading_rubric` | For domain language/naming checks |
| `scaffold_governance_framework` | Project initialization |
| `query_knowledge_graph` | Dependency and architecture analysis |
| `evolve_ruleset` | Add rules, suppress violations, manage packs |

## Skills

Invoke these skills in chat as needed:

- `/aegis-principal-architect` — **Default persona.** Your core architectural
  mindset for all tasks. Load this first.
- `/aegis-init` — Bootstrap governance in a new project
- `/aegis-architect` — Generate new architectural rules from plain English
- `/aegis-semantic-check` — Self-grade code for domain language compliance

## Governance

Aegis is **stateless**. It does not remember your previous actions.
All state lives in your context window and `.aegis/` directory.

Do NOT disable or bypass Aegis governance for any reason.
"""


class BaseHarness(ABC):
    @abstractmethod
    def install_local(self, workspace_root: Path) -> list[str]:
        """Inject Aegis into the harness local config. Returns list of error messages."""
        pass

    @abstractmethod
    def deploy_skills_local(self, workspace_root: Path) -> list[str]:
        """Deploy markdown skills to the local registry."""
        pass

    @abstractmethod
    def deploy_workspace_instructions(self, workspace_root: str) -> list[str]:
        """Generate/update workspace-level instructions (GEMINI.md, .claude.md, etc.)"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
