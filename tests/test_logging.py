import json
import logging

from app.logging_config import JsonFormatter


def test_json_formatter_basic():
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hello", args=(), exc_info=None,
    )
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "hello"
    assert payload["severity"] == "INFO"
    assert "time" in payload


def test_json_formatter_request_fields():
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1,
        msg="request", args=(), exc_info=None,
    )
    record.method = "GET"
    record.path = "/healthz"
    record.status = 200
    record.duration_ms = 1.23
    payload = json.loads(JsonFormatter().format(record))
    assert payload["method"] == "GET"
    assert payload["path"] == "/healthz"
    assert payload["status"] == 200
    assert payload["duration_ms"] == 1.23
