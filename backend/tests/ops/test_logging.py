import io
import json
import logging

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from apps.ops.logging import JsonFormatter, RedactionFilter, RequestIdFilter, request_id_var
from apps.ops.middleware import RequestIdMiddleware
from apps.ops.redaction import redact
from apps.ops.sentry import init_sentry, scrub_event


@pytest.mark.parametrize(
    "text",
    [
        "login failed for rider@example.com",
        "password=hunter2 next",
        'cookie: "sessionid=abc123def"',
        "Authorization: Bearer abcdef123456789",
        "connect postgres://undercut:s3cret@127.0.0.1:5432/undercut failed",
        '{"revalidate_secret": "topsecretvalue"}',
        "token=abc123&x=1",
    ],
)
def test_redact_removes_secrets(text):
    cleaned = redact(text)
    for leaked in ("rider@example.com", "hunter2", "abc123def", "abcdef123456789", "s3cret"):
        assert leaked not in cleaned
    assert "topsecretvalue" not in cleaned
    assert "abc123&" not in cleaned
    assert "[redacted]" in cleaned


@pytest.mark.parametrize("text", ["password=hunter2 a@b.co", "Bearer abcdef123456789 token: xyz"])
def test_redact_is_idempotent(text):
    once = redact(text)
    assert redact(once) == once


def test_redact_keeps_ordinary_text():
    text = "Handled 3 event(s) in 0.2 s for session:42"
    assert redact(text) == text


def _logger(stream):
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())
    handler.addFilter(RedactionFilter())
    log = logging.getLogger("undercut.test.json")
    log.handlers = [handler]
    log.propagate = False
    log.setLevel(logging.INFO)
    return log


def test_json_line_has_required_fields_and_no_email():
    stream = io.StringIO()
    log = _logger(stream)
    token = request_id_var.set("req-12345678")
    try:
        log.info("sent mail to %s", "someone@example.com")
    finally:
        request_id_var.reset(token)
    line = stream.getvalue().strip()
    data = json.loads(line)
    assert data["level"] == "INFO"
    assert data["logger"] == "undercut.test.json"
    assert data["request_id"] == "req-12345678"
    assert "someone@example.com" not in line
    assert "ts" in data


def test_json_line_includes_redacted_exception():
    stream = io.StringIO()
    log = _logger(stream)
    try:
        raise ValueError("bad value for owner@example.com")
    except ValueError:
        log.exception("failed")
    data = json.loads(stream.getvalue())
    assert "ValueError" in data["exception"]
    assert "owner@example.com" not in stream.getvalue()


def test_multiline_message_stays_one_json_line():
    stream = io.StringIO()
    _logger(stream).info("line one\nline two")
    assert len(stream.getvalue().strip().splitlines()) == 1


def _call(path="/api/v1/x/", header=None):
    request = (
        RequestFactory().get(path, HTTP_X_REQUEST_ID=header)
        if header
        else (RequestFactory().get(path))
    )
    seen = {}

    def view(req):
        seen["id"] = request_id_var.get()
        return HttpResponse("ok")

    return RequestIdMiddleware(view)(request), seen


def test_request_id_is_generated_and_echoed():
    response, seen = _call()
    assert response["X-Request-ID"] == seen["id"]
    assert len(seen["id"]) == 32
    assert request_id_var.get() == ""


def test_valid_request_id_is_kept():
    response, seen = _call(header="abc-12345678")
    assert response["X-Request-ID"] == "abc-12345678" == seen["id"]


def test_unsafe_request_id_is_replaced():
    response, _ = _call(header="bad id\r\nX-Evil: 1")
    assert response["X-Request-ID"] != "bad id\r\nX-Evil: 1"
    assert len(response["X-Request-ID"]) == 32


def test_access_log_has_no_query_string(caplog):
    caplog.set_level(logging.INFO, logger="undercut.request")
    _call(path="/api/v1/x/?token=supersecret")
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "supersecret" not in text
    assert "/api/v1/x/" in text


def test_health_requests_are_not_logged(caplog):
    caplog.set_level(logging.INFO, logger="undercut.request")
    _call(path="/api/health/")
    assert caplog.records == []


def test_scrub_event_drops_pii():
    event = {
        "message": "user a@b.co failed",
        "user": {"email": "a@b.co"},
        "request": {
            "cookies": {"sessionid": "x"},
            "data": {"password": "p"},
            "query_string": "token=1",
            "headers": {"Cookie": "sessionid=x", "Accept": "json", "Authorization": "Bearer abc"},
        },
        "exception": {"values": [{"value": "bad password=hunter2 for a@b.co"}]},
    }
    out = scrub_event(event)
    flat = json.dumps(out)
    assert "a@b.co" not in flat
    assert "hunter2" not in flat
    assert "user" not in out
    assert "cookies" not in out["request"] and "data" not in out["request"]
    assert out["request"]["headers"]["Cookie"] == "[redacted]"
    assert out["request"]["headers"]["Accept"] == "json"


def test_init_sentry_without_dsn_is_off():
    assert init_sentry("", environment="test") is False


def test_init_sentry_tolerates_missing_package(monkeypatch, caplog):
    monkeypatch.setitem(__import__("sys").modules, "sentry_sdk", None)  # makes the import fail
    assert init_sentry("https://k@example.invalid/1", environment="test") is False
    assert "not installed" in caplog.text
