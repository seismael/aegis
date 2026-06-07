import json
from pathlib import Path

from aegis.infrastructure.harnesses.base import (
    AEGIS_GOVERNANCE_DIRECTIVE,
    BaseHarness,
)


class GeminiHarness(BaseHarness):
    @property
    def name(self) -> str:
        return "gemini"

    def install_local(self, workspace_root: Path) -> list[str]:
        errors = []
        gemini_config = Path.home() / ".gemini.json"
        config = {}

        if gemini_config.exists():
            try:
                with open(gemini_config, encoding="utf-8") as f:
                    config = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                errors.append(f"Failed to read {gemini_config}: {e}")
                return errors

        if "mcpServers" not in config:
            config["mcpServers"] = {}
        config["mcpServers"]["aegis"] = {"command": "uvx", "args": ["aegis", "run"]}

        try:
            with open(gemini_config, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except OSError as e:
            errors.append(f"Failed to write {gemini_config}: {e}")
            return errors

        print(f"[Aegis] Injected governance directive into {gemini_config}")
        return errors

    def deploy_skills_local(self, workspace_root: Path) -> list[str]:
        # Currently no-op or placeholder for Gemini as per Step 2.
        return []

    def deploy_workspace_instructions(self, workspace_root: str) -> list[str]:
        path = Path(workspace_root) / "GEMINI.md"
        content = (
            "## Aegis Governance Protocol\n"
            "1. You MUST follow the instructions in [AGENTS.md](./AGENTS.md).\n"
            "2. Always ensure compliance by running `validate_architecture_compliance` before finishing a task.\n"
        )
        return self.safe_append_instruction(path, content, "Aegis Governance Protocol")
