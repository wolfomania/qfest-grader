# Copyright 2026 Qiskit Fall Fest 2026 Warsaw organisers.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.

"""Grading server location.

The publishable key is public by design: it only reaches the three grading
functions the server exposes. Override both values with environment variables
for a test server.
"""

import os

DEFAULT_SERVER_URL = "https://ldkuihmktahwmfcbbvwb.supabase.co"
DEFAULT_PUBLISHABLE_KEY = "sb_publishable_bssSWceOBBikDHD_HQydTg_3zyZuCoy"

SERVER_URL_ENV = "QFEST_GRADER_URL"
PUBLISHABLE_KEY_ENV = "QFEST_GRADER_KEY"


def server_url() -> str:
    return (os.environ.get(SERVER_URL_ENV) or DEFAULT_SERVER_URL).rstrip("/")


def publishable_key() -> str:
    return os.environ.get(PUBLISHABLE_KEY_ENV) or DEFAULT_PUBLISHABLE_KEY
