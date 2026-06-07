import os
from pathlib import Path


class Scorecard:
    """
    Manages the .aegis/AEGIS.md scorecard.
    """

    def __init__(self, workspace_root: str):
        self.root = Path(workspace_root)
        self.path = self.root / ".aegis" / "AEGIS.md"

    def generate(self, rules: list, violations: list, exceptions: list) -> str:
        """
        Generates the markdown content for the health scorecard.
        """
        total_rules = len(rules)
        
        if total_rules == 0:
            health = 100
        else:
            # Health is based on the percentage of rules that have ZERO violations
            rules_with_violations = len(set(getattr(v, "rule_id", v.get("rule_id")) if isinstance(v, dict) else v.rule_id for v in violations))
            health = int((1 - (rules_with_violations / total_rules)) * 100)

        # Clamp health score between 0 and 100
        health = max(0, min(100, health))

        content = "# 🛡️ Aegis Project Health Scorecard\n\n"
        content += f"**Health Score: {health}%**\n\n"
        content += "## 📜 Active Rules\n"
        for r in rules:
            if isinstance(r, dict):
                rid = r.get("id", "unknown")
                desc = r.get("description", "No description provided.")
            else:
                rid = getattr(r, "id", "unknown")
                desc = getattr(r, "description", "No description provided.")
            content += f"- **{rid}**: {desc}\n"

        if exceptions:
            from collections import Counter
            counts = Counter(exceptions)
            
            content += "\n## ⚠️ Exceptions (Technical Debt)\n"
            content += "The following rules have baseline exceptions (suppressed violations):\n\n"
            for rule_id, count in counts.items():
                if not rule_id: continue
                content += f"- **{rule_id}**: {count} baselined location{'s' if count > 1 else ''}\n"

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
