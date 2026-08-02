"""
Domain Observability Telemetry — re-exports from canonical location for backward compatibility.
The canonical implementation lives in aegis.domain.telemetry.
"""

from aegis.domain.telemetry import TelemetryExporterInterface, TelemetryRecorder

__all__ = ["TelemetryRecorder", "TelemetryExporterInterface"]
