import os

class ScorecardService:
    """
    Service for managing the root-level AEGIS.md scorecard.
    """
    def __init__(self, workspace_root: str):
        self.root = workspace_root
        self.path = os.path.join(workspace_root, "AEGIS.md")

    def generate(self, rules: list, violations: list, exceptions: list) -> str:
        """
        Generates the markdown content for the health scorecard.
        """
        total_rules = len(rules)
        active_violations = len(violations)
        health = 100 if total_rules == 0 else int((1 - (active_violations / total_rules)) * 100)
        
        content = "# 🛡️ Aegis Project Health Scorecard\n\n"
        content += f"**Health Score: {health}%**\n\n"
        content += "## 📜 Active Laws\n"
        for r in rules:
             # Handle both dict and object (Rule model)
             rid = r.get("id") if isinstance(r, dict) else r.id
             content += f"- {rid}\n"
        
        if exceptions:
            content += "\n## ⚠️ Exceptions (Technical Debt)\n"
            for e in exceptions:
                content += f"- {e}\n"
        
        return content

    def sync_to_disk(self, content: str):
        """
        Writes the scorecard content to AEGIS.md.
        """
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(content)
