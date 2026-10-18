# (C) Copyright IBM 2026
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
# reduced to counts, a number or sparse amplitudes before submission.

"""Qiskit Fall Fest 2026 Warsaw, Lab 0: grading functions."""

from typing import Any

from qfest_grader.answers import counts_answer, scalar_answer, statevector_answer
from qfest_grader.grade import grade_answer

_LAB = "lab0"


def grade_lab0_ex1() -> None:
    """Grade Exercise 1: check that your grader account works.

    Run save_account("<your email>") first, then call this function with no arguments.
    """
    grade_answer("hello", _LAB, "ex1")


def grade_lab0_ex2(counts: Any) -> None:
    """Grade Exercise 2: Sampler counts of H|0⟩.

    Args:
        counts: Dictionary of measurement counts, for example {'0': 497, '1': 503}.
    """
    grade_answer(counts, _LAB, "ex2", reduce=counts_answer)


def grade_lab0_ex3(exp_val: Any) -> None:
    """Grade Exercise 3: Estimator expectation value ⟨Z⟩ of H|0⟩.

    Args:
        exp_val: result[0].data.evs, a scalar (0-d array or float).
    """
    grade_answer(exp_val, _LAB, "ex3", reduce=scalar_answer)


def grade_lab0_ex4(sv: Any) -> None:
    """Grade Exercise 4: the 6-qubit statevector.

    Args:
        sv: Statevector of your 6-qubit circuit.
    """
    grade_answer(sv, _LAB, "ex4", reduce=statevector_answer)
