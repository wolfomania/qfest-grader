# (C) Copyright IBM 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
#
# Modified in 2026 by the Qiskit Fall Fest 2026 Warsaw organisers: calls the
# grading server's RPC endpoints with a publishable key instead of IBM's
# grading API with an IAM token; adds timeouts and retries.

"""HTTP transport to the grading server."""

from __future__ import annotations

import json
import time
from typing import Any

import requests

from qfest_grader import __version__
from qfest_grader.env import publishable_key, server_url

_TIMEOUT_SECONDS = 30
_RETRIES = 2
_RETRY_STATUS = {502, 503, 504}


class GraderError(Exception):
    """The grading server could not be reached or rejected the request."""


def call_rpc(function: str, body: dict[str, Any]) -> Any:
    """POST body to /rest/v1/rpc/<function> and return the decoded JSON reply."""
    url = f"{server_url()}/rest/v1/rpc/{function}"
    headers = {
        "apikey": publishable_key(),
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": f"qfest-grader/{__version__}",
    }
    payload = json.dumps(body, allow_nan=False)

    for attempt in range(_RETRIES + 1):
        try:
            response = requests.post(url, data=payload, headers=headers, timeout=_TIMEOUT_SECONDS)
        except requests.RequestException as err:
            if attempt < _RETRIES:
                time.sleep(1 + attempt)
                continue
            raise GraderError(
                f"Could not reach the grading server ({type(err).__name__}). "
                "Check your internet connection and run the cell again."
            ) from None
        if response.status_code in _RETRY_STATUS and attempt < _RETRIES:
            time.sleep(1 + attempt)
            continue
        if response.status_code == 200:
            return response.json()
        raise GraderError(_error_text(response))
    raise GraderError("The grading server did not answer.")  # pragma: no cover


def _error_text(response: requests.Response) -> str:
    try:
        detail = response.json().get("message")
    except ValueError:
        detail = None
    if not detail:
        detail = response.reason or "unexpected response"
    return f"The grading server returned {response.status_code}: {detail}"
