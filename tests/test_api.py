import pytest
import requests

from qfest_grader import api
from qfest_grader.api import GraderError, call_rpc


class FakeResponse:
    def __init__(self, status_code, body=None, reason="", text=""):
        self.status_code = status_code
        self._body = body
        self.reason = reason
        self.text = text

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(api.time, "sleep", lambda seconds: None)


def test_call_rpc_posts_json_with_publishable_key(monkeypatch):
    seen = {}

    def fake_post(url, data, headers, timeout):
        seen.update(url=url, data=data, headers=headers, timeout=timeout)
        return FakeResponse(200, {"ok": True})

    monkeypatch.setenv("QFEST_GRADER_URL", "https://grader.test/")
    monkeypatch.setenv("QFEST_GRADER_KEY", "sb_publishable_test")
    monkeypatch.setattr(api.requests, "post", fake_post)

    assert call_rpc("qf_submit", {"p_email": "a@b.pl"}) == {"ok": True}
    assert seen["url"] == "https://grader.test/rest/v1/rpc/qf_submit"
    assert seen["headers"]["apikey"] == "sb_publishable_test"
    assert "Authorization" not in seen["headers"]
    assert seen["data"] == '{"p_email": "a@b.pl"}'
    assert seen["timeout"] > 0


def test_call_rpc_retries_transient_errors(monkeypatch, no_sleep):
    replies = [FakeResponse(503), FakeResponse(200, {"ok": True})]
    monkeypatch.setattr(api.requests, "post", lambda *a, **k: replies.pop(0))
    assert call_rpc("qf_progress", {}) == {"ok": True}


def test_call_rpc_reports_server_message(monkeypatch):
    monkeypatch.setattr(api.requests, "post", lambda *a, **k: FakeResponse(400, {"message": "bad args"}))
    with pytest.raises(GraderError, match="400: bad args"):
        call_rpc("qf_submit", {})


def test_call_rpc_reports_status_without_json(monkeypatch):
    monkeypatch.setattr(api.requests, "post", lambda *a, **k: FakeResponse(413, None, reason="Payload Too Large"))
    with pytest.raises(GraderError, match="413: Payload Too Large"):
        call_rpc("qf_submit", {})


def test_call_rpc_reports_network_failure_after_retries(monkeypatch, no_sleep):
    calls = []

    def failing_post(*args, **kwargs):
        calls.append(1)
        raise requests.ConnectionError("down")

    monkeypatch.setattr(api.requests, "post", failing_post)
    with pytest.raises(GraderError, match="Could not reach the grading server"):
        call_rpc("qf_submit", {})
    assert len(calls) == 3


def test_call_rpc_rejects_nan():
    with pytest.raises(ValueError):
        call_rpc("qf_submit", {"x": float("nan")})


def test_call_rpc_rejects_a_reply_that_is_not_json(monkeypatch):
    monkeypatch.setattr(api.requests, "post", lambda *a, **k: FakeResponse(200, None))
    with pytest.raises(GraderError, match="invalid reply"):
        call_rpc("qf_submit", {})


def test_call_rpc_handles_error_bodies_that_are_not_objects(monkeypatch):
    monkeypatch.setattr(api.requests, "post", lambda *a, **k: FakeResponse(500, ["oops"], reason="Server Error"))
    with pytest.raises(GraderError, match="500: Server Error"):
        call_rpc("qf_submit", {})
