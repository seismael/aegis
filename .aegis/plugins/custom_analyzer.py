from aegis.domain.policy.models import Rule, EngineType, Severity, EnforcementMode
from aegis.domain.evaluation.ports import ArchitecturalViolation
from aegis.domain.evaluation.plugins.interfaces import CustomAnalyzerInterface

class EvilKeywordAnalyzer(CustomAnalyzerInterface):
    """A custom analyzer that detects EVIL_KEYWORD."""
    
    def register_rules(self) -> list[Rule]:
        return [
            Rule(
                id="plugin-no-evil",
                description="Custom plugin detected EVIL_KEYWORD",
                engine_type=EngineType.REGEX, # Arbitrary since we handle it manually
                severity=Severity.CRITICAL,
                mode=EnforcementMode.BLOCK,
                category="security",
                applies_to=["**/*.py"],
            )
        ]

    def analyze_file(self, file_path: str, content: str, rules: list[Rule]) -> list[ArchitecturalViolation]:
        rule_ids = [r.id for r in rules]
        with open("scratch/debug_plugin.txt", "a") as f:
            f.write(f"Analyzing {file_path} with {len(rules)} rules: {rule_ids}\n")
        violations = []
        for i, line in enumerate(content.splitlines(), start=1):
            if "EVIL_KEYWORD" in line:
                for r in rules:
                    if r.id == "plugin-no-evil":
                        violations.append(
                            ArchitecturalViolation(
                                file=file_path,
                                line=i,
                                rule_id=r.id,
                                description="Evil keyword found in custom plugin!"
                            )
                        )
        return violations

def register_analyzers():
    return [EvilKeywordAnalyzer()]
