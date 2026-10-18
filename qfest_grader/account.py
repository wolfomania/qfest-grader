# Copyright 2026 Qiskit Fall Fest 2026 Warsaw organisers.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.

"""Participant identity: the email saved once per environment."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

CONFIG_DIR_ENV = "QFEST_CONFIG_DIR"
EMAIL_ENV = "QFEST_EMAIL"
CONFIG_FILE = "grader.json"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PLACEHOLDER_DOMAINS = ("example.com", "example.org", "example.net")


class AccountError(ValueError):
    """The grader email is missing or invalid."""


def normalize_email(email: object) -> str:
    """Return the email trimmed and lower-cased, or raise AccountError."""
    if not isinstance(email, str):
        raise AccountError('Pass your email as text: save_account("<your email>").')
    normalized = email.strip().lower()
    if len(normalized) > 254 or not _EMAIL_RE.match(normalized):
        raise AccountError(f"{email!r} does not look like an email address.")
    if normalized.rsplit("@", 1)[1] in _PLACEHOLDER_DOMAINS:
        raise AccountError("Replace the placeholder with the email you registered with.")
    return normalized


def config_path() -> Path:
    base = os.environ.get(CONFIG_DIR_ENV)
    directory = Path(base) if base else Path.home() / ".qfest"
    return directory / CONFIG_FILE


def _write_private_json(path: Path, data: dict) -> None:
    """Write JSON readable only by the owner, replacing the file atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".grader-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise


def saved_email() -> Optional[str]:
    """The saved email, else the QFEST_EMAIL environment variable, else None."""
    path = config_path()
    if path.is_file():
        try:
            email = json.loads(path.read_text(encoding="utf-8")).get("email")
            return normalize_email(email)
        except (OSError, ValueError, AttributeError):
            pass
    env_email = os.environ.get(EMAIL_ENV)
    if env_email:
        try:
            return normalize_email(env_email)
        except AccountError:
            return None
    return None


def require_email() -> str:
    email = saved_email()
    if email is None:
        raise AccountError(
            'No grader account found. Run save_account("<your email>") with the email '
            "you registered with, then run this cell again."
        )
    return email


def save_account(email: str, verify: bool = True) -> None:
    """Save the email that identifies your submissions. Run once per environment.

    Args:
        email: The email you registered for Qiskit Fall Fest 2026 Warsaw.
        verify: Also register the email with the grading server (default True).
    """
    normalized = normalize_email(email)
    _write_private_json(
        config_path(),
        {"email": normalized, "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
    )
    if not verify:
        print(f"Grader account saved for {normalized}.")
        return

    from qfest_grader.api import GraderError, call_rpc

    try:
        response = call_rpc("qf_register", {"p_email": normalized, "p_client": _client_tag()})
    except GraderError as err:
        print(f"Grader account saved for {normalized}, but the server check failed: {err}")
        return
    if isinstance(response, dict) and response.get("ok"):
        print(f"{response.get('msg', 'Grader account saved.')} ✅")
    else:
        message = response.get("msg") if isinstance(response, dict) else response
        print(f"Grader account saved for {normalized}, but the server replied: {message}")


def _client_tag() -> str:
    import platform

    from qfest_grader import __version__

    return f"qfest-grader/{__version__} python/{platform.python_version()}"
