from unittest.mock import Mock, patch

import requests

from horshmon.probes import Result, _reason, http_check, tcp_check
from horshmon.store import transitions, update
from horshmon.tg import format_events, send_telegram


def test_http_ok():
    resp = Mock(status_code=200, text="hello world")
    with patch("horshmon.probes.requests.get", return_value=resp):
        result = http_check({"name": "t", "url": "https://x", "keyword": "world"}, 5)
    assert result.ok


def test_http_keyword_missing():
    resp = Mock(status_code=200, text="hello")
    with patch("horshmon.probes.requests.get", return_value=resp):
        result = http_check({"name": "t", "url": "https://x", "keyword": "world"}, 5)
    assert not result.ok


def test_http_error_status():
    resp = Mock(status_code=503, text="")
    with patch("horshmon.probes.requests.get", return_value=resp):
        result = http_check({"name": "t", "url": "https://x"}, 5)
    assert not result.ok


def test_http_expected_status():
    resp = Mock(status_code=302, text="")
    with patch("horshmon.probes.requests.get", return_value=resp):
        result = http_check({"name": "t", "url": "https://x", "expect": 200}, 5)
    assert not result.ok


def test_tcp_closed_port():
    result = tcp_check("t", "127.0.0.1", 1, 0.5)
    assert not result.ok
    assert result.detail in ("connection refused", "timed out")


def test_reason_unwraps_refused():
    outer = requests.exceptions.ConnectionError("HTTPConnectionPool(host='x', port=1): Max retries exceeded")
    outer.__context__ = ConnectionRefusedError("refused")
    assert _reason(outer) == "connection refused"


def test_reason_timeout():
    assert _reason(requests.exceptions.ConnectTimeout("timed out")) == "timed out"


def test_down_then_recovered():
    state = {"checks": {}}
    bad = Result("api", "http", False, "timeout")
    assert transitions(state, [bad])[0]["type"] == "down"
    update(state, [bad])
    good = Result("api", "http", True, "200 in 10 ms")
    assert transitions(state, [good])[0]["type"] == "up"


def test_no_event_when_unchanged():
    state = {"checks": {}}
    good = Result("api", "http", True, "200 in 10 ms")
    update(state, [good])
    assert transitions(state, [good]) == []


def test_warn_fires_once():
    state = {"checks": {}}
    cert = Result("site", "ssl", True, "expires in 5 days", warn=True)
    assert transitions(state, [cert])[0]["type"] == "warn"
    update(state, [cert])
    assert transitions(state, [cert]) == []


def test_signature_in_alert():
    text = format_events([{"type": "down", "result": Result("api", "http", False, "timeout")}])
    assert "[DOWN] api (http)" in text
    assert "by horshmarny" in text


def test_telegram_skipped_without_token():
    assert not send_telegram({"telegram": {"token": "", "chat_id": ""}}, "test")