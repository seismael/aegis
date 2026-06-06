from pathlib import Path

from aegis.infrastructure.harnesses.base import AGENTS_TEMPLATE, BaseHarness


class AiderHarness(BaseHarness):
    @property
    def name(self) -> str:
        return "aider"

    def install_local(self, workspace_root: Path) -> list[str]:
        errors = []
        aider_config = workspace_root / ".aider.conf.yml"
        directive = (
            "\n# Aegis Native Integration\n"
            "mcp-server: aegis run\n"
            "test-cmd: aegis run --headless-check\n"
            "auto-test: true\n"
        )

        try:
            with open(aider_config, "a", encoding="utf-8") as f:
                f.write(directive)
            print(f"[Aegis] Injected MCP configuration into {aider_config}")
        except OSError as e:
            errors.append(f"Failed to write {aider_config}: {e}")

        return errors

    def deploy_skills_local(self, workspace_root: Path) -> list[str]:
        # Aider doesn't have a separate global skills registry in the same way Claude does
        # or it uses AGENTS.md/instructions.
        return []

    def deploy_workspace_instructions(self, workspace_root: str) -> list[str]:
        errors = []
        path = Path(workspace_root) / "AGENTS.md"
        try:
            path.write_text(AGENTS_TEMPLATE, encoding="utf-8")
            print(f"[Aegis] Generated {path}")
        except OSError as e:
            errors.append(f"Failed to write {path}: {e}")
        return errors
