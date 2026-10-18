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
# Modified in 2026 by the Qiskit Fall Fest 2026 Warsaw organisers: answers are
# reduced to final values on the client and sent with the saved email to the
# grading server's RPC functions; teams and typeguard checks were removed.

"""Submit answers and print grading results and progress."""

from __future__ import annotations

import json
import platform
from functools import partial
from typing import Any, Callable, Optional

from qfest_grader import __version__
from qfest_grader.account import AccountError, require_email
from qfest_grader.answers import AnswerError
from qfest_grader.api import GraderError, call_rpc

# Payload limit; the server enforces its own limit too.
_MAX_ANSWER_BYTES = 64 * 1024


def _client_tag() -> str:
    try:
        import qiskit

        qiskit_version = qiskit.__version__
    except Exception:  # noqa: BLE001 - the tag is informational only
        qiskit_version = "unknown"
    return f"qfest-grader/{__version__} python/{platform.python_version()} qiskit/{qiskit_version}"


def _is_grade_response(response: Any) -> bool:
    return (
        isinstance(response, dict)
        and isinstance(response.get("passed"), bool)
        and isinstance(response.get("score"), (int, float))
        and isinstance(response.get("msg"), str)
    )


def grade_answer(
    answer: Any,
    lab: str,
    exercise: str,
    reduce: Optional[Callable[[Any], Any]] = None,
) -> None:
    """Reduce the answer, send it to the grading server and print the result."""

    print("Grading your answer. Please wait...\n")
    try:
        email = require_email()
        value = reduce(answer) if reduce is not None else answer
        answer_json = json.dumps(value, allow_nan=False)
        if len(answer_json) > _MAX_ANSWER_BYTES:
            print(
                f"Your answer is too large to submit ({len(answer_json) / 1024:.0f} kB, "
                f"limit {_MAX_ANSWER_BYTES // 1024} kB). Please simplify your answer and try again."
            )
            return
        response = call_rpc(
            "qf_submit",
            {
                "p_email": email,
                "p_lab": lab,
                "p_exercise": exercise,
                "p_answer": value,
                "p_client": _client_tag(),
            },
        )
    except AnswerError as err:
        print(determine_grade_response(passed=False, score=0, msg=str(err)))
        return
    except (AccountError, GraderError) as err:
        print(f"Failed: {err}")
        return
    except (TypeError, ValueError) as err:
        print(determine_grade_response(passed=False, score=0, msg=f"Your answer could not be read ({err})."))
        return

    if not _is_grade_response(response):
        print(
            "The grading server returned an unexpected response. Update the grader with "
            '%pip install -U "qfest-grader @ https://github.com/wolfomania/qfest-grader/archive/refs/heads/main.zip"'
        )
        return
    print(determine_grade_response(passed=response["passed"], score=response["score"], msg=response["msg"]))


def determine_grade_response(passed: bool, score: float, msg: str) -> str:
    """Format a human-readable message from a grade response."""
    score_line = f"\nYou scored {score} on this exercise."
    if passed:
        return msg + score_line
    if score > 0:
        return f"\nNot quite! {msg}{score_line}\nPlease review your answer and try again."
    return f"\nNot quite! {msg}\nPlease review your answer and try again."


# ------------------------------------------------------------------------------------------------
# Progress
# ------------------------------------------------------------------------------------------------


def _check_progress(lab_name: Optional[str] = None) -> None:
    """Fetch your progress and print a summary, for one lab or all labs."""

    print("Fetching your progress. Please wait...\n")
    try:
        email = require_email()
        response = call_rpc("qf_progress", {"p_email": email, "p_lab": lab_name})
    except (AccountError, GraderError) as err:
        print(f"Failed: {err}")
        return
    if (
        not isinstance(response, dict)
        or not isinstance(response.get("per_lab"), list)
        or not isinstance(response.get("challenge_aggregate"), dict)
    ):
        print("The grading server returned an unexpected response.")
        return
    print(determine_progress_response(response, lab_name=lab_name))


def create_check_progress_function() -> Callable[..., None]:
    return partial(_check_progress)


def _format_lab(lab: dict) -> list[str]:
    lines = [
        f'Lab "{lab["name"]}" — '
        f"{lab['num_exercises_passed']}/{lab['num_exercises']} passed, "
        f"score {lab['score_total']}",
    ]
    for exercise in lab["per_exercise"]:
        icon = "✅" if exercise["passed"] else "⬜"
        lines.append(f"  {icon} {exercise['name']} — score {exercise['score']}")
    return lines


def determine_progress_response(response: dict, lab_name: Optional[str] = None) -> str:
    """Format a human-readable progress summary."""
    if lab_name is not None:
        lab = next((lab for lab in response["per_lab"] if lab["name"] == lab_name), None)
        if lab is None:
            return f'No lab named "{lab_name}" is open for grading yet.'
        return "\n".join(["📊 Your progress", "", *_format_lab(lab)])

    aggregate = response["challenge_aggregate"]
    lines = [
        "📊 Your progress",
        "",
        f"Exercises passed: {aggregate['num_exercises_passed']}/{aggregate['num_exercises']}",
        f"Total score: {aggregate['score_total']}",
    ]
    for lab in response["per_lab"]:
        lines.append("")
        lines.extend(_format_lab(lab))
    return "\n".join(lines)
