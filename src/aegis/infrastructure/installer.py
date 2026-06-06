"""
Aegis V4 Agent-Native Installer.
Injects Aegis directly into the cognition and execution loops
of Claude and Aider via their native configuration files.
Deploys bundled markdown skills to the agent's skill registries.
No adapters. MCP is the universal protocol.
"""

from pathlib import Path

from aegis.infrastructure.harnesses.aider import AiderHarness
from aegis.infrastructure.harnesses.base import (
    AGENTS_TEMPLATE,
)
from aegis.infrastructure.harnesses.claude import ClaudeHarness
from aegis.infrastructure.harnesses.gemini import GeminiHarness


class AgentNativeInstaller:
    """
    Injects Aegis directly into the cognition and execution loops
    of the target AI coding agents by creating local workspace configuration files.
    Deploys bundled skills to the local workspace.
    """

    def __init__(self):
        self.harnesses = {
            "claude": ClaudeHarness(),
            "aider": AiderHarness(),
            "gemini": GeminiHarness(),
        }

    def init_workspace(
        self,
        workspace_root: str = ".",
        target_tool: str | None = None,
        instructions_only: bool = False,
    ):
        if target_tool and target_tool not in self.harnesses:
            raise ValueError(
                f"Unsupported tool: {target_tool}. Supported: {', '.join(self.harnesses.keys())}"
            )

        workspace_path = Path(workspace_root).resolve()
        targets = [target_tool] if target_tool else list(self.harnesses.keys())
        errors = []

        # Generate universal mcp.json
        if not instructions_only:
            errors.extend(self._generate_mcp_json(workspace_path))

        for t in targets:
            h = self.harnesses.get(t)
            if h:
                if not instructions_only:
                    errors.extend(h.install_local(workspace_path))
                    errors.extend(h.deploy_skills_local(workspace_path))
                errors.extend(h.deploy_workspace_instructions(str(workspace_path)))

        if errors:
            print("[Aegis] Init completed with warnings:")
            for e in errors:
                print(f"  WARN: {e}")

    def _generate_mcp_json(self, workspace_path: Path) -> list[str]:
        import json
        errors = []
        mcp_json_path = workspace_path / "mcp.json"
        config = {
            "mcpServers": {
                "aegis-kernel": {
                    "command": "uvx",
                    "args": ["aegis", "run"]
                }
            }
        }
        try:
            with open(mcp_json_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            print(f"[Aegis] Generated {mcp_json_path}")
        except OSError as e:
            errors.append(f"Failed to write {mcp_json_path}: {e}")
        return errors

    @staticmethod
    def generate_agents_template(target_dir: str) -> str:
        """Generate AGENTS.md with mandatory governance protocol."""
        path = Path(target_dir) / "AGENTS.md"
        path.write_text(AGENTS_TEMPLATE)
        return str(path)
