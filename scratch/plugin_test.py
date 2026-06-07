import asyncio
from pathlib import Path
from aegis.kernel.server import AegisKernel
from aegis.domain.policy.models import Rule
from aegis.domain.evaluation.ports import ArchitecturalViolation

class MockPluginAnalyzer:
    """A dummy analyzer that flags the word 'DANGER'."""
    def __init__(self, workspace_root: str):
        self.workspace_root = workspace_root
        
    def analyze_file(self, file_path: str, content: str, rules: list[Rule]) -> list[ArchitecturalViolation]:
        violations = []
        for i, line in enumerate(content.splitlines(), start=1):
            if "DANGER" in line:
                violations.append(
                    ArchitecturalViolation(
                        file=file_path,
                        line=i,
                        rule_id="custom-danger-rule",
                        description="Found DANGER in file via Custom Plugin",
                    )
                )
        return violations

async def main():
    root = "c:/dev/projects/aegis"
    
    # Write a test file
    target_file = Path(root) / "scratch" / "danger_file.py"
    target_file.write_text("print('This is fine')\nprint('DANGER level maximum!')\n", encoding="utf-8")
    
    kernel = AegisKernel(workspace_root=root)
    
    if kernel.evaluation:
        kernel.evaluation.extra_analyzers.append(MockPluginAnalyzer(root))
        print("Mock plugin injected.")
        
    res = await kernel.check_architecture(["scratch/danger_file.py"])
    with open("scratch/plugin_test_output.txt", "w", encoding="utf-8") as f:
        f.write(res)

if __name__ == "__main__":
    asyncio.run(main())
