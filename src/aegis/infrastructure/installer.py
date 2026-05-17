import os
import sys
import shutil
import json
import subprocess

class AegisInstaller:
    """
    Universal Installer for Aegis.
    Detects the environment and injects appropriate configs and skills.
    """
    def __init__(self, target_dir: str = "."):
        self.target_dir = os.path.abspath(target_dir)
        self.aegis_dir = os.path.join(self.target_dir, ".aegis")

    def install(self):
        print(f"📦 Installing Aegis into {self.target_dir}...")
        
        # 1. Create .aegis directory
        if not os.path.exists(self.aegis_dir):
            os.makedirs(self.aegis_dir)
            
        # 2. Setup Claude Skills
        self._setup_claude()
        
        # 3. Setup Aider Config
        self._setup_aider()
        
        # 4. Setup Git Hooks
        self._setup_git_hooks()
        
        print("\n✅ Aegis installation complete!")
        print("Run `/aegis-init` in your AI chat window to begin architectural discovery.")

    def _setup_claude(self):
        # Identify skills source within the installed package
        current_dir = os.path.dirname(__file__)
        skills_src = os.path.abspath(os.path.join(current_dir, "..", "..", "..", ".claude", "skills"))
        skills_dest = os.path.abspath(os.path.join(self.target_dir, ".claude", "skills"))
        
        # Don't copy if src and dest are identical (avoids lock errors in dev)
        if skills_src == skills_dest:
            print("  ✓ Claude skills already present in source.")
            return

        if os.path.exists(skills_src):
            if not os.path.exists(skills_dest):
                os.makedirs(skills_dest)
            for item in os.listdir(skills_src):
                shutil.copy2(os.path.join(skills_src, item), os.path.join(skills_dest, item))
            print("  ✓ Claude skills injected.")

    def _setup_aider(self):
        aider_conf_path = os.path.join(self.target_dir, ".aider.conf.yml")
        aider_config = {
            "mcp-servers": [
                f"uv run aegis-kernel"
            ],
            "read": [
                "AGENTS.md",
                "SPEC.md",
                ".aegis/rules.yaml"
            ]
        }
        
        with open(aider_conf_path, "w", encoding="utf-8") as f:
            import yaml
            yaml.dump(aider_config, f)
            
        print("  ✓ Aider configuration (.aider.conf.yml) mapped.")

    def _setup_git_hooks(self):
        # Delegate to the CLI logic
        subprocess.run(["uv", "run", "aegis", "setup-hooks"], cwd=self.target_dir, capture_output=True)
        print("  ✓ Git pre-commit hooks wired.")

    @staticmethod
    def entry_point():
        installer = AegisInstaller()
        installer.install()

if __name__ == "__main__":
    AegisInstaller.entry_point()
