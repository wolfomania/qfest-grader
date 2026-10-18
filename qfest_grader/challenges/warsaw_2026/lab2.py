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
# reduced to circuit facts (operation sequences and counts, depth, CX pairs,
# measurements, resets and if_else blocks) and returned values before
# submission; the server compares them with the Warsaw answer key.

"""Qiskit Fall Fest 2026 Warsaw, Lab 2: grading functions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Callable

from qfest_grader.answers import AnswerError, _as_int
from qfest_grader.facts import (
    call,
    dynamic_circuit_facts,
    int_list,
    op_sequence,
    plain_number,
    require_circuit,
    string_list,
    undirected_edges,
)
from qfest_grader.grade import grade_answer

_LAB = "lab2"
_REPEAT_NS = (0, 1, 2, 3, 5, 10)
_GHZ_NS = (4, 6, 8, 10, 12, 20)
_PARAMS_NS = (4, 6, 8)
_ERRORS = ("X error", "Y error", "Z error")
_EXPERIMENTS = ("bit-flip sensitive", "phase-flip sensitive")
_PARAM_KEYS = (
    "Number of qubits",
    "Depth",
    "2-qubit depth",
    "Gates",
    "Multi-qubit gates",
    "Number of ancillas",
)


def grade_lab2_ex1(basis_operations: Any, coupling_map: Any) -> None:
    """Grade Exercise 1: ibm_fez basis operations and coupling map."""
    grade_answer((basis_operations, coupling_map), _LAB, "ex1", reduce=_ex1_answer)


def _ex1_answer(answer: tuple[Any, Any]) -> dict[str, Any]:
    basis_operations, coupling_map = answer
    return {
        "ops": string_list(basis_operations, "basis_operations"),
        "edges": undirected_edges(coupling_map, "coupling_map"),
    }


def _repeated_circuits(fn: Any, name: str) -> dict[str, Any]:
    facts = {}
    for n in _REPEAT_NS:
        what = f"{name}({n})"
        circuit = require_circuit(call(fn, n, what=what), what)
        if circuit.num_qubits > 20 or circuit.depth() > 100:
            raise AnswerError(
                f"The circuit for n={n} is too large (num_qubits={circuit.num_qubits}, "
                f"depth={circuit.depth()}) compared to the expected answer."
            )
        facts[str(n)] = {"qubits": circuit.num_qubits, "seq": op_sequence(circuit)}
    return facts


def grade_lab2_ex2(repeated_x_circuit: Callable[[int], Any]) -> None:
    """Grade Exercise 2: the repeated X circuit."""
    grade_answer(
        repeated_x_circuit, _LAB, "ex2", reduce=lambda fn: _repeated_circuits(fn, "repeated_x_circuit")
    )


def grade_lab2_ex3(repeated_x_meas_x_circuit: Callable[[int], Any]) -> None:
    """Grade Exercise 3: the repeated X circuit measured in the X basis."""
    grade_answer(
        repeated_x_meas_x_circuit,
        _LAB,
        "ex3",
        reduce=lambda fn: _repeated_circuits(fn, "repeated_x_meas_x_circuit"),
    )


def _ex4_answer(answer: Any) -> dict[str, dict[str, bool]]:
    if not isinstance(answer, Mapping) or set(answer) != set(_ERRORS):
        submitted = set(answer) if isinstance(answer, Mapping) else set()
        raise AnswerError(
            f"The answer dictionary must contain exactly the keys {sorted(_ERRORS)}. "
            f"Missing: {sorted(set(_ERRORS) - submitted)}. Unexpected: {sorted(submitted - set(_ERRORS), key=str)}."
        )
    result = {}
    for error in _ERRORS:
        contents = answer[error]
        if not isinstance(contents, Mapping) or set(contents) != set(_EXPERIMENTS):
            submitted = set(contents) if isinstance(contents, Mapping) else set()
            raise AnswerError(
                f"For {error}, provide exactly the keys {sorted(_EXPERIMENTS)}. "
                f"Missing: {sorted(set(_EXPERIMENTS) - submitted)}. "
                f"Unexpected: {sorted(submitted - set(_EXPERIMENTS), key=str)}."
            )
        for experiment in _EXPERIMENTS:
            visibility = contents[experiment]
            if visibility is None:
                raise AnswerError(
                    f"Please replace None with True or False for '{error}' in the '{experiment}' experiment."
                )
            if not isinstance(visibility, bool):
                raise AnswerError(
                    f"The value for '{error}' in the '{experiment}' experiment must be True or False, "
                    f"not {type(visibility).__name__}."
                )
        result[error] = {experiment: contents[experiment] for experiment in _EXPERIMENTS}
    return result


def grade_lab2_ex4(answer_pauli_visibility: Any) -> None:
    """Grade Exercise 4: which Pauli errors each experiment detects."""
    grade_answer(answer_pauli_visibility, _LAB, "ex4", reduce=_ex4_answer)


def build_test_circuits() -> list[Any]:
    """The five circuits on which count_swap_gates is checked."""
    from qiskit import QuantumCircuit

    c1 = QuantumCircuit(2)
    c1.swap(0, 1)
    c2 = QuantumCircuit(3)
    c2.swap(0, 1)
    c2.swap(1, 2)
    c3 = QuantumCircuit(4)
    c3.swap(0, 1)
    c3.swap(1, 2)
    c3.swap(2, 3)
    c4 = QuantumCircuit(2)
    c4.h(0)
    c4.cx(0, 1)
    c5 = QuantumCircuit(3)
    c5.h(0)
    c5.cx(0, 1)
    c5.swap(1, 2)
    return [c1, c2, c3, c4, c5]


def _ex5_answer(answer: tuple[Any, Any, Any]) -> dict[str, Any]:
    initial_layout, basis_gates, count_swap_gates = answer
    swaps = [
        _as_int(call(count_swap_gates, circuit, what="count_swap_gates"), "count_swap_gates(circuit)")
        for circuit in build_test_circuits()
    ]
    return {
        "layout": int_list(initial_layout, "initial_layout"),
        "basis": string_list(basis_gates, "basis_gates"),
        "swaps": swaps,
    }


def grade_lab2_ex5(initial_layout: Any, basis_gates: Any, count_swap_gates: Callable[[Any], int]) -> None:
    """Grade Exercise 5: initial_layout, basis_gates and the count_swap_gates function."""
    grade_answer((initial_layout, basis_gates, count_swap_gates), _LAB, "ex5", reduce=_ex5_answer)


def _ghz_facts(build_circuit: Any, n: int) -> dict[str, Any]:
    what = f"build_circuit({n})"
    return dynamic_circuit_facts(require_circuit(call(build_circuit, n, what=what), what))


def grade_lab2_ex6(build_circuit: Callable[[int], Any]) -> None:
    """Grade Exercise 6: the dynamic GHZ circuit builder."""
    grade_answer(
        build_circuit, _LAB, "ex6", reduce=lambda fn: {str(n): _ghz_facts(fn, n) for n in _GHZ_NS}
    )


def _params_answer(params: Any) -> dict[str, Any]:
    if not isinstance(params, Mapping):
        raise AnswerError(
            f"quantum_circuit_params must return a dictionary, got {type(params).__name__}."
        )
    missing = [key for key in _PARAM_KEYS if key not in params]
    if missing:
        raise AnswerError(f"quantum_circuit_params must return the key(s) {', '.join(repr(k) for k in missing)}.")
    result: dict[str, Any] = {}
    for key in _PARAM_KEYS:
        value = params[key]
        if key == "Gates" and isinstance(value, Mapping):
            result[key] = {str(name): _as_int(count, f"The count of {name!r} in 'Gates'") for name, count in value.items()}
        else:
            result[key] = plain_number(value, f"'{key}'")
    return result


def _ex7_answer(answer: tuple[Any, Any]) -> dict[str, Any]:
    quantum_circuit_params, build_circuit = answer
    result = {}
    for n in _PARAMS_NS:
        what = f"build_circuit({n})"
        circuit = require_circuit(call(build_circuit, n, what=what), what)
        params = call(quantum_circuit_params, circuit, what=f"quantum_circuit_params(build_circuit({n}))")
        result[str(n)] = {"build": dynamic_circuit_facts(circuit), "params": _params_answer(params)}
    return result


def grade_lab2_ex7(
    quantum_circuit_params: Callable[[Any], Any],
    build_circuit: Callable[[int], Any],
) -> None:
    """Grade Exercise 7: quantum_circuit_params on the Exercise 6 circuits."""
    grade_answer((quantum_circuit_params, build_circuit), _LAB, "ex7", reduce=_ex7_answer)
