# Copyright 2026 Qiskit Fall Fest 2026 Warsaw organisers.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.

"""Grader client for the Qiskit Fall Fest 2026 Warsaw lab notebooks.

Set up once per environment::

    from qfest_grader import save_account
    save_account("<your email>")

Then call the ``grade_labN_exM`` functions from ``qfest_grader.challenges.warsaw_2026``.
"""

__version__ = "0.1.2"

from qfest_grader.account import AccountError, save_account, saved_email  # noqa: E402
from qfest_grader.challenges.warsaw_2026 import check_progress  # noqa: E402

__all__ = ["AccountError", "__version__", "check_progress", "save_account", "saved_email"]
