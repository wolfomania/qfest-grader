import pytest


@pytest.fixture(autouse=True)
def isolated_account(tmp_path, monkeypatch):
    """Keep every test away from the real ~/.qfest and environment."""
    monkeypatch.setenv("QFEST_CONFIG_DIR", str(tmp_path / "qfest"))
    monkeypatch.delenv("QFEST_EMAIL", raising=False)
    monkeypatch.delenv("QFEST_GRADER_URL", raising=False)
    monkeypatch.delenv("QFEST_GRADER_KEY", raising=False)
    return tmp_path / "qfest"


@pytest.fixture
def rpc_calls(monkeypatch):
    """Replace the network call; tests set .reply and read .calls."""

    class FakeRpc:
        def __init__(self):
            self.calls = []
            self.reply = {"passed": True, "score": 1.0, "msg": "ok"}

        def __call__(self, function, body):
            self.calls.append((function, body))
            if isinstance(self.reply, Exception):
                raise self.reply
            return self.reply

    fake = FakeRpc()
    monkeypatch.setattr("qfest_grader.grade.call_rpc", fake)
    monkeypatch.setattr("qfest_grader.api.call_rpc", fake)
    return fake
