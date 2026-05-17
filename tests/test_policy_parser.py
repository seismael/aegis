import yaml
from unittest.mock import MagicMock, patch

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

    def _write_rules(self, tmp_path, data: dict):
        """Helper to write a rules.yaml file."""
        rules_dir = tmp_path / ".aegis"
        rules_dir.mkdir(parents=True, exist_ok=True)
        rules_file = rules_dir / "rules.yaml"
        with open(rules_file, "w", encoding="utf-8") as f:
            yaml.dump(data, f)
        return str(rules_file)

    @staticmethod
    def _mock_response(text: str, status: int = 200):
        """Create a mock httpx response."""
        resp = MagicMock()
        resp.status_code = status
        resp.text = text
        resp.raise_for_status.return_value = None
        return resp

    def test_extends_merges_remote_rules(self, tmp_path):
        """extends key fetches remote rules and merges with local."""
        rules_file = self._write_rules(
            tmp_path,
            {
                "extends": "https://org.example.com/base-rules.yaml",
                "rules": [
                    {"id": "local-only", "description": "local", "query": "(module) @m"}
                ],
            },
        )
        remote_yaml = yaml.dump(
            {
                "rules": [
                    {
                        "id": "org-base",
                        "description": "No prints",
                        "query": r"print\(",
                        "severity": "HIGH",
                        "mode": "block",
                    }
                ]
            }
        )

        with patch("httpx.get") as mock_get:
            mock_get.return_value = self._mock_response(remote_yaml)
            parser = PolicyParser()
            rules = parser.parse_rules(rules_file)

        assert len(rules) == 2
        ids = {r.id for r in rules}
        assert "org-base" in ids
        assert "local-only" in ids

    def test_extends_local_overrides_remote(self, tmp_path):
        """Local rule with same ID overrides remote rule."""
        rules_file = self._write_rules(
            tmp_path,
            {
                "extends": "https://org.example.com/base-rules.yaml",
                "rules": [
                    {
                        "id": "dup-rule",
                        "description": "local version",
                        "query": "(module) @m",
                        "severity": "HIGH",
                        "mode": "warn",
                    }
                ],
            },
        )
        remote_yaml = yaml.dump(
            {
                "rules": [
                    {
                        "id": "dup-rule",
                        "description": "remote version",
                        "query": r"print\(",
                        "severity": "CRITICAL",
                        "mode": "block",
                    }
                ]
            }
        )

        with patch("httpx.get") as mock_get:
            mock_get.return_value = self._mock_response(remote_yaml)
            parser = PolicyParser()
            rules = parser.parse_rules(rules_file)

        assert len(rules) == 1
        assert rules[0].mode.value == "warn"
        assert "local version" in rules[0].description

    def test_extends_network_error_returns_local_only(self, tmp_path):
        """When remote fetch fails, local rules still load."""
        rules_file = self._write_rules(
            tmp_path,
            {
                "extends": "https://org.example.com/base-rules.yaml",
                "rules": [
                    {"id": "local", "description": "local", "query": "(module) @m"}
                ],
            },
        )

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = ConnectionError("No route to host")
            parser = PolicyParser()
            rules = parser.parse_rules(rules_file)

        assert len(rules) == 1
        assert rules[0].id == "local"

    def test_extends_timeout_returns_local_only(self, tmp_path):
        """When remote fetch times out, local rules still load."""
        rules_file = self._write_rules(
            tmp_path,
            {
                "extends": "https://org.example.com/base-rules.yaml",
                "rules": [
                    {"id": "local", "description": "local", "query": "(module) @m"}
                ],
            },
        )

        with patch("httpx.get") as mock_get:
            mock_get.side_effect = TimeoutError("Timed out")
            parser = PolicyParser()
            rules = parser.parse_rules(rules_file)

        assert len(rules) == 1
        assert rules[0].id == "local"

    def test_extends_invalid_remote_yaml_ignored(self, tmp_path):
        """Invalid YAML from remote URL is ignored, local rules still load."""
        rules_file = self._write_rules(
            tmp_path,
            {
                "extends": "https://org.example.com/base-rules.yaml",
                "rules": [
                    {"id": "local", "description": "local", "query": "(module) @m"}
                ],
            },
        )

        with patch("httpx.get") as mock_get:
            mock_get.return_value = self._mock_response("not: valid: yaml: [[")
            parser = PolicyParser()
            rules = parser.parse_rules(rules_file)

        assert len(rules) == 1
        assert rules[0].id == "local"

    def test_extends_no_remote_rules_key_returns_empty_remote(self, tmp_path):
        """Remote response without 'rules' key contributes nothing."""
        rules_file = self._write_rules(
            tmp_path,
            {
                "extends": "https://org.example.com/base-rules.yaml",
                "rules": [
                    {"id": "local", "description": "local", "query": "(module) @m"}
                ],
            },
        )

        with patch("httpx.get") as mock_get:
            mock_get.return_value = self._mock_response(yaml.dump({"version": 1}))
            parser = PolicyParser()
            rules = parser.parse_rules(rules_file)

        assert len(rules) == 1
        assert rules[0].id == "local"

    def test_extends_without_local_rules_still_loads_remote(self, tmp_path):
        """Remote rules load even when no local rules section exists."""
        rules_file = self._write_rules(
            tmp_path,
            {
                "extends": "https://org.example.com/base-rules.yaml",
            },
        )
        remote_yaml = yaml.dump(
            {
                "rules": [
                    {
                        "id": "org-rule",
                        "description": "From org",
                        "query": r"print\(",
                        "severity": "HIGH",
                        "mode": "block",
                    }
                ]
            }
        )

        with patch("httpx.get") as mock_get:
            mock_get.return_value = self._mock_response(remote_yaml)
            parser = PolicyParser()
            rules = parser.parse_rules(rules_file)

        assert len(rules) == 1
        assert rules[0].id == "org-rule"
