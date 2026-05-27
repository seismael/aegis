"""
Aegis V4 Agent-Native Installer.
Injects Aegis directly into the cognition and execution loops
of Claude and Aider via their native configuration files.
Deploys bundled markdown skills to the agent's skill registries.
No adapters. MCP is the universal protocol.
"""

from pathlib import Path
from aegis.infrastructure.harnesses.base import (
    AEGIS_GOVERNANCE_DIRECTIVE,
    AEGIS_SKILL_FILES,
    AGENTS_TEMPLATE,
)
from aegis.infrastructure.harnesses.claude import ClaudeHarness
from aegis.infrastructure.harnesses.aider import AiderHarness
from aegis.infrastructure.harnesses.gemini import GeminiHarness


class AgentNativeInstaller:
    """
    Injects Aegis directly into the cognition and execution loops
    of the target AI coding agents. Deploys bundled skills globally.
    """

    def __init__(self):
        self.home = Path.home()
        self.harnesses = {
            "claude": ClaudeHarness(self.home),
            "aider": AiderHarness(self.home),
            "gemini": GeminiHarness(self.home),
        }

    def install(
        self,
        target_tool: str | None = None,
        workspace_root: str | None = None,
        instructions_only: bool = False,
    ):
        if target_tool and target_tool not in self.harnesses:
            raise ValueError(
                f"Unsupported tool: {target_tool}. Supported: {', '.join(self.harnesses.keys())}"
            )

        targets = [target_tool] if target_tool else list(self.harnesses.keys())
        errors = []

        for t in targets:
            h = self.harnesses.get(t)
            if h:
                if not instructions_only:
                    errors.extend(h.install())
                    errors.extend(h.deploy_skills())
                if workspace_root:
                    errors.extend(h.deploy_workspace_instructions(workspace_root))

        if errors:
            print("[Aegis] Install completed with warnings:")
            for e in errors:
                print(f"  WARN: {e}")

    @staticmethod
    def generate_agents_template(target_dir: str) -> str:
        """Generate AGENTS.md with mandatory governance protocol."""
        path = Path(target_dir) / "AGENTS.md"
        path.write_text(AGENTS_TEMPLATE)
        return str(path)
