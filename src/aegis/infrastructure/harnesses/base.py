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

    def safe_append_instruction(self, path: Path, content: str, identifier: str = "Aegis") -> list[str]:
        """Safely append instruction to a markdown file without overwriting existing content."""
        errors = []
        try:
            if path.exists():
                existing = path.read_text(encoding="utf-8")
                if identifier in existing:
                    return []  # Already governed
                new_content = f"{existing.strip()}\n\n{content}"
            else:
                new_content = content

            path.write_text(new_content, encoding="utf-8")
            print(f"[Aegis] Safely updated {path.name}")
        except OSError as e:
            errors.append(f"Failed to safely update {path.name}: {e}")
        return errors

    @property
    @abstractmethod
    def name(self) -> str:
        pass
