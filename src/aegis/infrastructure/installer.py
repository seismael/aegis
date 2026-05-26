"""
Aegis V4 Agent-Native Installer.
Injects Aegis directly into the cognition and execution loops
of Claude and Aider via their native configuration files.
Deploys bundled markdown skills to the agent's skill registries.
No adapters. MCP is the universal protocol.
"""

import json
from importlib import resources
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


class AgentNativeInstaller:
    """
    Injects Aegis directly into the cognition and execution loops
    of the target AI coding agents. Deploys bundled skills globally.
    """

    def __init__(self):
        self.home = Path.home()

    def install(self, target_tool: str | None = None):
        if target_tool and target_tool not in ("claude", "aider"):
            raise ValueError(
                f"Unsupported tool: {target_tool}. Supported: claude, aider"
            )

        errors = []
        if not target_tool or target_tool == "claude":
            errors.extend(self._inject_claude())
            errors.extend(self._deploy_claude_skills())
        if not target_tool or target_tool == "aider":
            errors.extend(self._inject_aider())

        if errors:
            print("[Aegis] Install completed with warnings:")
            for e in errors:
                print(f"  WARN: {e}")

    def _inject_claude(self):
        errors = []
        claude_config = self.home / ".claude.json"
        config = {}
        if claude_config.exists():
            try:
                with open(claude_config, encoding="utf-8-sig") as f:
                    config = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                errors.append(f"Failed to read {claude_config}: {e}")
                return errors

        if "mcpServers" not in config:
            config["mcpServers"] = {}
        config["mcpServers"]["aegis"] = {"command": "aegis", "args": ["run"]}

        existing_instructions = config.get("customInstructions", "")
        if "Aegis Microkernel" not in existing_instructions:
            config["customInstructions"] = (
                f"{existing_instructions}\n\n{AEGIS_GOVERNANCE_DIRECTIVE}".strip()
            )

        try:
            with open(claude_config, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except OSError as e:
            errors.append(f"Failed to write {claude_config}: {e}")
            return errors

        print(f"[Aegis] Injected governance directive into {claude_config}")
        return errors

    def _deploy_claude_skills(self):
        errors = []
        skills_dir = self.home / ".claude" / "skills"
        try:
            skills_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            errors.append(f"Failed to create skills directory {skills_dir}: {e}")
            return errors

        deployed = 0
        for skill_name in AEGIS_SKILL_FILES:
            try:
                content = (
                    resources.files("aegis.resources.skills")
                    .joinpath(skill_name)
                    .read_text()
                )
                target = skills_dir / skill_name
                target.write_text(content)
                deployed += 1
            except Exception:
                pass

        if deployed:
            print(f"[Aegis] Deployed {deployed} skills to {skills_dir}")
        return errors

    def _inject_aider(self):
        errors = []
        aider_config = self.home / ".aider.conf.yml"
        directive = (
            "\n# Aegis Native Integration\n"
            "mcp-server: aegis run\n"
            "test-cmd: aegis run --headless-check\n"
            "auto-test: true\n"
        )

        try:
            with open(aider_config, "a") as f:
                f.write(directive)
        except OSError as e:
            errors.append(f"Failed to write {aider_config}: {e}")
            return errors

        print(f"[Aegis] Injected MCP configuration into {aider_config}")
        return errors

    @staticmethod
    def generate_agents_template(target_dir: str) -> str:
        """Generate AGENTS.md with mandatory governance protocol."""
        path = Path(target_dir) / "AGENTS.md"
        path.write_text(AGENTS_TEMPLATE)
        return str(path)
