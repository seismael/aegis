from unittest.mock import patch

from aegis.core.container.app import Container


class TestContainerDegradedMode:
    """Container init resilience — degraded mode tests."""

    def test_normal_init(self, tmp_path):
        """Container initialises all services in a normal project."""
        c = Container(str(tmp_path))
        assert c.governance_service is not None
        assert c.evaluation_service is not None
        assert c.evolution_service is not None
        assert c.baseline_manager is not None
        assert c.diff_provider is not None
        assert c.policy_parser is not None
        assert c.remediation_synthesizer is not None
        assert not c.is_degraded()
        assert c.init_errors == []

    def test_init_errors_empty_when_all_ok(self, tmp_path):
        c = Container(str(tmp_path))
        assert c.init_errors == []

    def test_baseline_manager_permission_error(self, tmp_path):
        """Permission error in BaselineManager does not crash init."""
        with patch(
            "aegis.core.container.app.BaselineManager",
            side_effect=PermissionError("access denied"),
        ):
            c = Container(str(tmp_path))
        assert c.is_degraded()
        assert any("baseline_manager" in e for e in c.init_errors)
        assert c.baseline_manager is None
        # Governance depends on baseline_manager
        assert c.governance_service is None

    def test_evolution_service_permission_error(self, tmp_path):
        """Permission error in EvolutionService does not crash init."""
        with patch(
            "aegis.core.container.app.EvolutionService",
            side_effect=PermissionError("access denied"),
        ):
            c = Container(str(tmp_path))
        assert c.is_degraded()
        assert any("evolution_service" in e for e in c.init_errors)
        assert c.evolution_service is None
        # Other services remain functional
        assert c.baseline_manager is not None
        assert c.governance_service is not None

    def test_git_diff_provider_not_a_repo(self, tmp_path):
        """GitDiffProvider handles non-repo gracefully (no crash)."""
        c = Container(str(tmp_path))
        assert c.diff_provider is not None or not c.is_degraded()
        # GitDiffProvider returns None repo but doesn't raise

    def test_governance_service_unavailable(self, tmp_path):
        """When governance_service is None, get_active_violations is not callable."""
        with patch(
            "aegis.core.container.app.BaselineManager",
            side_effect=PermissionError("access denied"),
        ):
            c = Container(str(tmp_path))
        assert c.governance_service is None
        # load_rules still works
        assert c.load_rules() == []

    def test_evaluation_service_unavailable(self, tmp_path):
        """When evaluation_service dependencies fail, service is None."""
        with patch(
            "aegis.core.container.app.BaselineManager",
            side_effect=PermissionError("access denied"),
        ):
            c = Container(str(tmp_path))
        assert c.evaluation_service is None
        assert c.governance_service is None

    def test_plugin_registry_init_error(self, tmp_path):
        """Plugin load failure does not crash Container init."""
        with patch(
            "aegis.core.container.app.PluginRegistry.load_plugins",
            side_effect=RuntimeError("plugin boom"),
        ):
            c = Container(str(tmp_path))
        assert c.is_degraded()
        assert any("plugins" in e for e in c.init_errors)
        # Core services still available
        assert c.baseline_manager is not None
        assert c.evaluation_service is not None
        assert c.governance_service is not None

    def test_discover_project_root_fallback(self):
        """_discover_project_root falls back to CWD when no marker found."""
        c = Container.__new__(Container)
        with patch("aegis.core.container.app.os.getcwd", return_value="/some/path"):
            with patch("aegis.core.container.app.os.path.exists", return_value=False):
                root = c._discover_project_root()
        assert root == "/some/path"

    def test_is_degraded_true_on_failure(self, tmp_path):
        """is_degraded returns True when a component failed."""
        with patch(
            "aegis.core.container.app.BaselineManager",
            side_effect=PermissionError("access denied"),
        ):
            c = Container(str(tmp_path))
        assert c.is_degraded()

    def test_is_degraded_false_on_success(self, tmp_path):
        c = Container(str(tmp_path))
        assert not c.is_degraded()

    def test_multiple_init_errors_collected(self, tmp_path):
        """Multiple failures are all recorded in init_errors."""
        with patch(
            "aegis.core.container.app.BaselineManager",
            side_effect=PermissionError("bm fail"),
        ):
            with patch(
                "aegis.core.container.app.EvolutionService",
                side_effect=PermissionError("evo fail"),
            ):
                c = Container(str(tmp_path))
        assert len(c.init_errors) >= 2
        assert c.governance_service is None
        assert c.evolution_service is None

    def test_load_rules_empty_dir(self, tmp_path):
        """load_rules returns empty when no rules dir exists."""
        c = Container(str(tmp_path))
        assert c.load_rules() == []

    def test_custom_mcp_tools_empty_by_default(self, tmp_path):
        c = Container(str(tmp_path))
        assert c.custom_mcp_tools == []

    def test_loaded_plugins_empty_by_default(self, tmp_path):
        c = Container(str(tmp_path))
        assert c.loaded_plugins == []


class TestContainerInitErrorsProperty:
    """Verify init_errors property behaves correctly."""

    def test_init_errors_immutable_copy(self, tmp_path):
        """init_errors returns a copy, not the internal list."""
        with patch(
            "aegis.core.container.app.BaselineManager",
            side_effect=PermissionError("fail"),
        ):
            c = Container(str(tmp_path))
        errors = c.init_errors
        errors.append("tampered")
        assert "tampered" not in c.init_errors
