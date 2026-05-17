import pytest
import yaml
from aegis.domain.policy.parser import PolicyParser
from aegis.core.models.governance import Severity

class TestPolicyParser:
    """
    Test suite for the PolicyParser.
    """
    def test_parse_rules_from_yaml(self, tmp_path):
        rules_dir = tmp_path / ".aegis"
        rules_dir.mkdir()
        rules_file = rules_dir / "rules.yaml"
        
        rules_data = {
            "rules": [
                {
                    "id": "test-rule",
                    "description": "Test description",
                    "query": "(module) @mod",
                    "severity": "HIGH",
                    "mode": "block"
                }
            ]
        }
        
        with open(rules_file, "w", encoding="utf-8") as f:
            yaml.dump(rules_data, f)
            
        parser = PolicyParser()
        rules = parser.parse_rules(str(rules_file))
        
        assert len(rules) == 1
        assert rules[0].id == "test-rule"
        assert rules[0].description == "Test description"
        assert rules[0].severity == Severity.HIGH
