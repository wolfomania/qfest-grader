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
# Modified in 2026 by the Qiskit Fall Fest 2026 Warsaw organisers: grading
# functions of the Warsaw labs; progress comes from the Warsaw grading server.

"""Qiskit Fall Fest 2026 Warsaw: grading functions."""

from qfest_grader.grade import create_check_progress_function

from .lab0 import (
    grade_lab0_ex1,
    grade_lab0_ex2,
    grade_lab0_ex3,
    grade_lab0_ex4,
)
from .lab1 import (
    grade_lab1_ex1,
    grade_lab1_ex2,
    grade_lab1_ex3,
    grade_lab1_ex4,
    grade_lab1_ex5,
    grade_lab1_ex6,
    grade_lab1_ex7,
)
from .lab2 import (
    grade_lab2_ex1,
    grade_lab2_ex2,
    grade_lab2_ex3,
    grade_lab2_ex4,
    grade_lab2_ex5,
    grade_lab2_ex6,
    grade_lab2_ex7,
)
from .lab3 import (
    grade_lab3_ex1,
    grade_lab3_ex2,
    grade_lab3_ex3,
    grade_lab3_ex4,
    grade_lab3_ex5,
)

check_progress = create_check_progress_function()

__all__ = [
    "check_progress",
    "grade_lab0_ex1",
    "grade_lab0_ex2",
    "grade_lab0_ex3",
    "grade_lab0_ex4",
    "grade_lab1_ex1",
    "grade_lab1_ex2",
    "grade_lab1_ex3",
    "grade_lab1_ex4",
    "grade_lab1_ex5",
    "grade_lab1_ex6",
    "grade_lab1_ex7",
    "grade_lab2_ex1",
    "grade_lab2_ex2",
    "grade_lab2_ex3",
    "grade_lab2_ex4",
    "grade_lab2_ex5",
    "grade_lab2_ex6",
    "grade_lab2_ex7",
    "grade_lab3_ex1",
    "grade_lab3_ex2",
    "grade_lab3_ex3",
    "grade_lab3_ex4",
    "grade_lab3_ex5",
]
