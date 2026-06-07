from pathlib import Path

from aegis.infrastructure.harnesses.base import AGENTS_TEMPLATE, BaseHarness


class AiderHarness(BaseHarness):
    @property
    def name(self) -> str:
        return "aider"

    def install_local(self, workspace_root: Path) -> list[str]:
        errors = []
        aider_config = Path.home() / ".aider.conf.yml"

        directive = (
            "\n# Aegis Native Integration\n"
            "mcp-server: uvx aegis run\n"
            "test-cmd: uvx aegis run --headless-check\n"
            "auto-test: true\n"
        )

        try:
            self.safe_append_instruction(aider_config, directive)
            print(f"[Aegis] Injected governance directive into {aider_config}")
        except OSError as e:
            errors.append(f"Failed to update Aider config {aider_config}: {e}")

        return errors

    def deploy_skills_local(self, workspace_root: Path) -> list[str]:
        # Aider doesn't have a separate global skills registry in the same way Claude does
        # or it uses AGENTS.md/instructions.
        return []

    def deploy_workspace_instructions(self, workspace_root: str) -> list[str]:
        path = Path(workspace_root) / "AGENTS.md"
        return self.safe_append_instruction(path, AGENTS_TEMPLATE, "Aegis V4 Governance")
