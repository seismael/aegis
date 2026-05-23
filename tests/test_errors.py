"""Tests for the structured MCP error protocol."""

import json

from aegis.kernel.errors import (
    ERR_CONTAINER_NOT_INIT,
    error,
    ok,
    warn,
)


class TestErrorFunction:
    def test_error_returns_json_string(self):
        result = error(ERR_CONTAINER_NOT_INIT, "Test error")
        data = json.loads(result)
        assert data["success"] is False
        assert data["error_code"] == ERR_CONTAINER_NOT_INIT
        assert data["message"] == "Test error"

    def test_error_with_hint(self):
        result = error("ERR_DEMO", "Test", hint="Do this instead")
        data = json.loads(result)
        assert data["hint"] == "Do this instead"

    def test_error_without_hint(self):
        result = error("ERR_DEMO", "Test")
        data = json.loads(result)
        assert "hint" not in data


class TestOkFunction:
    def test_ok_returns_plain_string(self):
        assert ok("Success") == "Success"


class TestWarnFunction:
    def test_warn_prefixed(self):
        assert warn("Something") == "WARN: Something"
