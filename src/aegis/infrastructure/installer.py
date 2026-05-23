"""
Aegis V4 Agent-Native Installer.
Injects Aegis directly into the cognition and execution loops
of Claude and Aider via their native configuration files.
No adapters. MCP is the universal protocol.
"""

import json
from pathlib import Path

AEGIS_GOVERNANCE_DIRECTIVE = (
    "CRITICAL GOVERNANCE DIRECTIVE: "
    "You are governed by the Aegis Microkernel. "
    "Before declaring ANY coding task complete, you MUST execute the "
    "`validate_architecture_compliance` MCP tool. If it returns violations, "
    "you MUST remediate the code natively before proceeding."
)


class AgentNativeInstaller:
    """
    Injects Aegis directly into the cognition and execution loops
    of the target AI coding agents.
    """

    def __init__(self):
        self.home = Path.home()

    def install(self, target_tool: str | None = None):
        if not target_tool or target_tool == "claude":
            self._inject_claude()
        if not target_tool or target_tool == "aider":
            self._inject_aider()
        if target_tool and target_tool not in ("claude", "aider"):
            raise ValueError(
                f"Unsupported tool: {target_tool}. Supported: claude, aider"
            )

    def _inject_claude(self):
        claude_config = self.home / ".claude.json"
        config = {}
        if claude_config.exists():
            with open(claude_config, "r") as f:
                config = json.load(f)

        if "mcpServers" not in config:
            config["mcpServers"] = {}
        config["mcpServers"]["aegis"] = {"command": "aegis", "args": ["run"]}

        existing_instructions = config.get("customInstructions", "")
        if "Aegis Microkernel" not in existing_instructions:
            config["customInstructions"] = (
                f"{existing_instructions}\n\n{AEGIS_GOVERNANCE_DIRECTIVE}".strip()
            )

        with open(claude_config, "w") as f:
            json.dump(config, f, indent=2)

        print(f"[Aegis] Injected governance directive into {claude_config}")

    def _inject_aider(self):
        aider_config = self.home / ".aider.conf.yml"
        directive = (
            "\n# Aegis Native Integration\n"
            "mcp-server: aegis run\n"
            "test-cmd: aegis run --check\n"
            "auto-test: true\n"
        )

        with open(aider_config, "a") as f:
            f.write(directive)

        print(f"[Aegis] Injected MCP configuration into {aider_config}")
