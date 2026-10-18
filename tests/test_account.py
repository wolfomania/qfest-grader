import json
import os
import stat

import pytest

from qfest_grader.account import AccountError, config_path, normalize_email, require_email, save_account, saved_email
from qfest_grader.api import GraderError


def test_normalize_email_trims_and_lowercases():
    assert normalize_email("  Ada.Lovelace@Uni.EDU.pl ") == "ada.lovelace@uni.edu.pl"


@pytest.mark.parametrize("bad", ["", "no-at-sign", "a@b", "two@@x.pl", "a b@x.pl", "x" * 250 + "@x.pl", None, 42])
def test_normalize_email_rejects_invalid(bad):
    with pytest.raises(AccountError):
        normalize_email(bad)


def test_normalize_email_rejects_placeholder_domains():
    with pytest.raises(AccountError, match="placeholder"):
        normalize_email("you@example.com")


def test_save_account_writes_private_file(capsys):
    save_account("Student@Uni.pl", verify=False)

    path = config_path()
    assert json.loads(path.read_text())["email"] == "student@uni.pl"
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert "saved for student@uni.pl" in capsys.readouterr().out
    assert saved_email() == "student@uni.pl"


def test_save_account_overwrites_previous_email():
    save_account("first@uni.pl", verify=False)
    save_account("second@uni.pl", verify=False)
    assert saved_email() == "second@uni.pl"


def test_saved_email_falls_back_to_environment(monkeypatch):
    monkeypatch.setenv("QFEST_EMAIL", " Env@Uni.pl ")
    assert saved_email() == "env@uni.pl"


def test_saved_file_takes_precedence_over_environment(monkeypatch):
    save_account("file@uni.pl", verify=False)
    monkeypatch.setenv("QFEST_EMAIL", "env@uni.pl")
    assert saved_email() == "file@uni.pl"


def test_corrupt_config_falls_back_to_environment(monkeypatch):
    path = config_path()
    path.parent.mkdir(parents=True)
    path.write_text("{not json")
    monkeypatch.setenv("QFEST_EMAIL", "env@uni.pl")
    assert saved_email() == "env@uni.pl"


def test_require_email_explains_setup_when_missing():
    with pytest.raises(AccountError, match="save_account"):
        require_email()


def test_save_account_registers_with_server(rpc_calls, capsys):
    rpc_calls.reply = {"ok": True, "msg": "Grader account saved for student@uni.pl."}
    save_account("student@uni.pl")

    function, body = rpc_calls.calls[0]
    assert function == "qf_register"
    assert body["p_email"] == "student@uni.pl"
    assert "✅" in capsys.readouterr().out


def test_save_account_keeps_local_copy_when_server_fails(rpc_calls, capsys):
    rpc_calls.reply = GraderError("offline")
    save_account("student@uni.pl")

    assert saved_email() == "student@uni.pl"
    assert "server check failed: offline" in capsys.readouterr().out


def test_save_account_reports_server_refusal(rpc_calls, capsys):
    rpc_calls.reply = {"ok": False, "msg": "busy"}
    save_account("student@uni.pl")
    assert "server replied: busy" in capsys.readouterr().out
