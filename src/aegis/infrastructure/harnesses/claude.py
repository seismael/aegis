import json
from importlib import resources
from pathlib import Path

from aegis.infrastructure.harnesses.base import (
    AEGIS_SKILL_FILES,
    BaseHarness,
)


class ClaudeHarness(BaseHarness):
    @property
    def name(self) -> str:
        return "claude"

    def install_local(self, workspace_root: Path) -> list[str]:
        errors = []
        claude_config = Path.home() / ".claude.json"
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
        config["mcpServers"]["aegis"] = {"command": "uvx", "args": ["aegis", "run"]}

        try:
            with open(claude_config, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except OSError as e:
            errors.append(f"Failed to write {claude_config}: {e}")
            return errors

        print(f"[Aegis] Injected governance directive into {claude_config}")
        return errors

    def deploy_skills_local(self, workspace_root: Path) -> list[str]:
        errors = []
        skills_dir = workspace_root / ".aegis" / "skills"
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
                    .read_text(encoding="utf-8")
                )
                target = skills_dir / skill_name
                target.write_text(content, encoding="utf-8")
                deployed += 1
            except Exception as e:
                errors.append(f"Failed to deploy skill {skill_name}: {e}")

        if deployed:
            print(f"[Aegis] Deployed {deployed} skills to {skills_dir}")
        return errors

    def deploy_workspace_instructions(self, workspace_root: str) -> list[str]:
        path = Path(workspace_root) / "CLAUDE.md"
        content = (
            "## Aegis Governance Protocol\n"
            "This workspace is governed by the Aegis Microkernel.\n"
            "Please refer to the [AGENTS.md](./AGENTS.md) for the full governance protocol.\n"
        )
        return self.safe_append_instruction(path, content, "Aegis Microkernel")
