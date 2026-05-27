import os
from pathlib import Path


class Scorecard:
    """
    Manages the root-level AEGIS.md scorecard.
    """

    def __init__(self, workspace_root: str):
        self.root = Path(workspace_root)
        self.path = self.root / "AEGIS.md"

    def generate(self, rules: list, violations: list, exceptions: list) -> str:
        """
        Generates the markdown content for the health scorecard.
        """
        total_rules = len(rules)
        active_violations = len(violations)

        if total_rules == 0:
            health = 100
        else:
            health = int((1 - (active_violations / total_rules)) * 100)

        # Clamp health score between 0 and 100
        health = max(0, min(100, health))

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
        Writes the scorecard content to AEGIS.md atomically.
        """
        tmp = str(self.path) + ".tmp"
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, self.path)
