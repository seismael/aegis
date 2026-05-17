import yaml

from aegis.core.models.governance import EngineType, Severity
from aegis.domain.policy.parser import PolicyParser


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
                    "mode": "block",
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
        # Default engine_type for backward compatibility
        assert rules[0].engine_type == EngineType.TREE_SITTER

    def test_parse_engine_type_from_yaml(self, tmp_path):
        rules_dir = tmp_path / ".aegis"
        rules_dir.mkdir()
        rules_file = rules_dir / "rules.yaml"

        rules_data = {
            "rules": [
                {
                    "id": "graph-rule",
                    "description": "No domain->infra imports",
                    "engine_type": "graph",
                    "query": "disallowed_import",
                    "severity": "HIGH",
                    "mode": "block",
                    "metadata": {"source": "domain", "target": "infrastructure"},
                },
                {
                    "id": "regex-rule",
                    "description": "No hardcoded secrets",
                    "engine_type": "regex",
                    "query": r"password\s*=",
                    "severity": "CRITICAL",
                    "mode": "block",
                },
            ]
        }

        with open(rules_file, "w", encoding="utf-8") as f:
            yaml.dump(rules_data, f)

        parser = PolicyParser()
        rules = parser.parse_rules(str(rules_file))

        assert len(rules) == 2
        assert rules[0].engine_type == EngineType.GRAPH
        assert rules[1].engine_type == EngineType.REGEX
        assert rules[0].metadata["source"] == "domain"
        assert rules[0].metadata["target"] == "infrastructure"
