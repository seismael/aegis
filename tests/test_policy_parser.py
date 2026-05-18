from unittest.mock import MagicMock, patch

import yaml

from aegis.domain.policy.models import EngineType, RuleCategory, Severity
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


class TestPolicyParserDirectory:
    """Test suite for PolicyParser.parse_directory()."""

    def test_empty_dir_returns_empty(self, tmp_path):
        parser = PolicyParser()
        rules = parser.parse_directory(str(tmp_path / "nonexistent"))
        assert rules == []

    def test_empty_yaml_dir_returns_empty(self, tmp_path):
        (tmp_path / "rules").mkdir()
        parser = PolicyParser()
        rules = parser.parse_directory(str(tmp_path / "rules"))
        assert rules == []

    def test_single_pack_parsed(self, tmp_path):
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        (rules_dir / "architecture.yaml").write_text(
            yaml.dump(
                {"rules": [{"id": "layer-rule", "description": "Layer isolation"}]}
            ),
            encoding="utf-8",
        )
        parser = PolicyParser()
        rules = parser.parse_directory(str(rules_dir))
        assert len(rules) == 1
        assert rules[0].id == "layer-rule"
        assert rules[0].category == RuleCategory.ARCHITECTURE

    def test_multiple_packs_aggregate(self, tmp_path):
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        (rules_dir / "architecture.yaml").write_text(
            yaml.dump({"rules": [{"id": "arch-1", "description": "Arch rule"}]}),
            encoding="utf-8",
        )
        (rules_dir / "security.yaml").write_text(
            yaml.dump({"rules": [{"id": "sec-1", "description": "Sec rule"}]}),
            encoding="utf-8",
        )
        parser = PolicyParser()
        rules = parser.parse_directory(str(rules_dir))
        assert len(rules) == 2
        assert {r.id for r in rules} == {"arch-1", "sec-1"}

    def test_explicit_category_overrides_filename(self, tmp_path):
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        (rules_dir / "style.yaml").write_text(
            yaml.dump(
                {
                    "rules": [
                        {
                            "id": "sec-rule",
                            "description": "Security rule",
                            "category": "security",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        parser = PolicyParser()
        rules = parser.parse_directory(str(rules_dir))
        assert len(rules) == 1
        assert rules[0].category == RuleCategory.SECURITY

    def test_skips_invalid_rules(self, tmp_path):
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        (rules_dir / "architecture.yaml").write_text(
            yaml.dump(
                {
                    "rules": [
                        {"id": "valid", "description": "Good rule"},
                        {"id": "invalid", "description": 12345},
                    ]
                }
            ),
            encoding="utf-8",
        )
        parser = PolicyParser()
        rules = parser.parse_directory(str(rules_dir))
        assert len(rules) == 1
        assert rules[0].id == "valid"

    # --- Recursive scanning (rglob) tests ---

    def test_subdirectory_packs_loaded(self, tmp_path):
        """Rules in subdirectories are found via rglob."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        arch_dir = rules_dir / "architecture"
        arch_dir.mkdir()
        (arch_dir / "rules.yaml").write_text(
            yaml.dump({"rules": [{"id": "arch-1", "description": "Arch rule"}]}),
            encoding="utf-8",
        )
        parser = PolicyParser()
        rules = parser.parse_directory(str(rules_dir))
        assert len(rules) == 1
        assert any(r.id == "arch-1" for r in rules)

    def test_subdirectory_category_inference(self, tmp_path):
        """Rules in subdirectory get category from parent dir name, not stem."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        arch_dir = rules_dir / "architecture"
        arch_dir.mkdir()
        (arch_dir / "rules.yaml").write_text(
            yaml.dump({"rules": [{"id": "arch-1", "description": "Arch rule"}]}),
            encoding="utf-8",
        )
        parser = PolicyParser()
        rules = parser.parse_directory(str(rules_dir))
        assert len(rules) == 1
        assert rules[0].category == RuleCategory.ARCHITECTURE

    def test_mixed_root_and_subdirectory(self, tmp_path):
        """Root-level files and subdirectory packs coexist."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        # Root-level file
        (rules_dir / "security.yaml").write_text(
            yaml.dump({"rules": [{"id": "sec-1", "description": "Sec"}]}),
            encoding="utf-8",
        )
        # Subdirectory pack
        style_dir = rules_dir / "style"
        style_dir.mkdir()
        (style_dir / "rules.yaml").write_text(
            yaml.dump({"rules": [{"id": "style-1", "description": "Style"}]}),
            encoding="utf-8",
        )
        parser = PolicyParser()
        rules = parser.parse_directory(str(rules_dir))
        assert len(rules) == 2
        ids = {r.id for r in rules}
        assert ids == {"sec-1", "style-1"}

    def test_pack_yaml_skipped(self, tmp_path):
        """pack.yaml metadata files are skipped."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        arch_dir = rules_dir / "architecture"
        arch_dir.mkdir()
        (arch_dir / "pack.yaml").write_text(
            yaml.dump({"name": "architecture", "version": "1.0.0"}),
            encoding="utf-8",
        )
        (arch_dir / "rules.yaml").write_text(
            yaml.dump({"rules": [{"id": "arch-1", "description": "Arch"}]}),
            encoding="utf-8",
        )
        parser = PolicyParser()
        rules = parser.parse_directory(str(rules_dir))
        assert len(rules) == 1
        assert rules[0].id == "arch-1"

    def test_explicit_category_in_subdirectory(self, tmp_path):
        """Explicit category overrides subdirectory name."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        sec_dir = rules_dir / "style"
        sec_dir.mkdir()
        (sec_dir / "rules.yaml").write_text(
            yaml.dump(
                {
                    "rules": [
                        {
                            "id": "sec-rule",
                            "description": "Security rule in style dir",
                            "category": "security",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        parser = PolicyParser()
        rules = parser.parse_directory(str(rules_dir))
        assert len(rules) == 1
        assert rules[0].category == RuleCategory.SECURITY

    def test_invalid_category_directory_skips_rules(self, tmp_path):
        """Subdirectory name that isn't a valid RuleCategory → rules are skipped."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        bad_dir = rules_dir / "custom"
        bad_dir.mkdir()
        (bad_dir / "rules.yaml").write_text(
            yaml.dump({"rules": [{"id": "r1", "description": "in custom dir"}]}),
            encoding="utf-8",
        )
        arch_dir = rules_dir / "architecture"
        arch_dir.mkdir()
        (arch_dir / "rules.yaml").write_text(
            yaml.dump({"rules": [{"id": "arch-1", "description": "Arch rule"}]}),
            encoding="utf-8",
        )
        parser = PolicyParser()
        rules = parser.parse_directory(str(rules_dir))
        assert len(rules) == 1
        assert rules[0].id == "arch-1"

    def test_explicit_category_in_invalid_directory(self, tmp_path):
        """Rules in invalid directory with explicit category still load."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        bad_dir = rules_dir / "custom"
        bad_dir.mkdir()
        (bad_dir / "rules.yaml").write_text(
            yaml.dump(
                {
                    "rules": [
                        {
                            "id": "r1",
                            "description": "rule with explicit category",
                            "category": "architecture",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        parser = PolicyParser()
        rules = parser.parse_directory(str(rules_dir))
        assert len(rules) == 1
        assert rules[0].category == RuleCategory.ARCHITECTURE
