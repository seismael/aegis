"""Tests for TelemetryRecorder."""

from aegis.domain.observability.telemetry import TelemetryRecorder


class TestTelemetryRecorder:
    """Test suite for TelemetryRecorder — architectural observability."""

    def test_record_remediation_and_read(self, tmp_path):
        """A remediation event is written then readable."""
        t = TelemetryRecorder(str(tmp_path))
        t.record_remediation("r1")
        data = t._load()
        assert len(data["remediations"]) == 1
        assert data["remediations"][0]["rule_id"] == "r1"

    def test_record_check(self, tmp_path):
        """A check event is written then readable."""
        t = TelemetryRecorder(str(tmp_path))
        t.record_check(3)
        data = t._load()
        assert len(data["checks"]) == 1
        assert data["checks"][0]["violation_count"] == 3

    def test_insights_empty(self, tmp_path):
        """Insights on empty telemetry returns zeros."""
        t = TelemetryRecorder(str(tmp_path))
        insights = t.get_insights()
        assert insights["total_remediations"] == 0
        assert insights["total_checks"] == 0
        assert insights["check_success_rate"] == 0.0

    def test_insights_with_data(self, tmp_path):
        """Insights aggregate multiple events correctly."""
        t = TelemetryRecorder(str(tmp_path))
        t.record_remediation("r1")
        t.record_remediation("r1")
        t.record_remediation("r2")
        t.record_check(0)
        t.record_check(3)

        insights = t.get_insights()
        assert insights["total_remediations"] == 3
        assert insights["total_checks"] == 2
        assert insights["check_success_rate"] == 0.5
        assert insights["total_violations_found"] == 3
        assert insights["remediation_by_rule"]["r1"] == 2
        assert insights["remediation_by_rule"]["r2"] == 1

    def test_display_insights_format(self, tmp_path):
        """display_insights returns markdown with key headers."""
        t = TelemetryRecorder(str(tmp_path))
        output = t.display_insights()
        assert "Aegis Insights Scorecard" in output
        assert "checks run" in output
        assert "remediations applied" in output
        assert "success rate" in output
