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
# Modified in 2026 by the Qiskit Fall Fest 2026 Warsaw organisers: circuits are
# reduced to their depth, multi-qubit gate positions and final state (sparse
# amplitudes, or stabilizer expectation values for Exercise 7) before submission.

"""Qiskit Fall Fest 2026 Warsaw, Lab 1: grading functions."""

from functools import partial
from typing import Any

from qfest_grader.answers import circuit_state_answer, ghz_stabilizer_answer, int_dict_answer
from qfest_grader.grade import grade_answer

_LAB = "lab1"


def grade_lab1_ex1(qc: Any) -> None:
    """Grade Exercise 1: Bell state (|01⟩ + |10⟩) / √2."""
    grade_answer(qc, _LAB, "ex1", reduce=circuit_state_answer)


def grade_lab1_ex2(predictions: Any) -> None:
    """Grade Exercise 2: predicted depths of Circuit A and Circuit B.

    Example:
        grade_lab1_ex2({"a": your_answer_a, "b": your_answer_b})
    """
    grade_answer(predictions, _LAB, "ex2", reduce=partial(int_dict_answer, keys=("a", "b")))


def grade_lab1_ex3(qc: Any) -> None:
    """Grade Exercise 3: depth-5 16-qubit GHZ via recursive fan-out."""
    grade_answer(qc, _LAB, "ex3", reduce=circuit_state_answer)


def grade_lab1_ex4(qc: Any) -> None:
    """Grade Exercise 4: 3-qubit GHZ using only nearest-neighbor CX gates."""
    grade_answer(qc, _LAB, "ex4", reduce=circuit_state_answer)


def grade_lab1_ex5(qc: Any) -> None:
    """Grade Exercise 5: depth-4 5-qubit GHZ from the middle."""
    grade_answer(qc, _LAB, "ex5", reduce=circuit_state_answer)


def grade_lab1_ex6(qc: Any) -> None:
    """Grade Exercise 6: 7-qubit GHZ on the T-shape heavy-hex subgraph."""
    grade_answer(qc, _LAB, "ex6", reduce=circuit_state_answer)


def grade_lab1_ex7(qc: Any) -> None:
    """Grade Exercise 7: 64-qubit BFS spanning-tree GHZ on FakeTorino."""
    grade_answer(qc, _LAB, "ex7", reduce=ghz_stabilizer_answer)
