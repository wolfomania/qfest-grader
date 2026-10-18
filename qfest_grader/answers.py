# Copyright 2026 Qiskit Fall Fest 2026 Warsaw organisers.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.

"""Reduce notebook objects to the small JSON values the server checks.

The server compares final values only: counts, numbers, sparse statevectors,
circuit facts (depth, multi-qubit gate positions) and stabilizer expectation
values. It never receives or runs a circuit.
"""

from __future__ import annotations

import math
import numbers
from collections.abc import Mapping
from typing import Any

import numpy as np

MAX_STATEVECTOR_QUBITS = 20
MAX_AMPLITUDES = 1024
MAX_GATES = 2000
AMPLITUDE_CUTOFF = 1e-9
_SKIPPED_OPS = {"barrier", "measure", "delay", "reset"}


class AnswerError(ValueError):
    """The submitted object has the wrong type or shape."""


def _as_int(value: Any, what: str) -> int:
    if isinstance(value, bool):
        raise AnswerError(f"{what} must be a whole number, not {value!r}.")
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real) and float(value).is_integer():
        return int(value)
    raise AnswerError(f"{what} must be a whole number, got {value!r}.")


def counts_answer(counts: Any) -> dict[str, int]:
    """Measurement counts as {outcome: shots}."""
    if not isinstance(counts, Mapping):
        raise AnswerError("Submit the counts dictionary, for example {'0': 497, '1': 503}.")
    return {str(key): _as_int(value, f"The count for {key!r}") for key, value in counts.items()}


def scalar_answer(value: Any) -> float:
    """A single finite real number, such as an expectation value."""
    array = np.asarray(value)
    if array.size != 1:
        raise AnswerError(
            f"Submit a single number, got shape {array.shape}. "
            "Use result[0].data.evs for one expectation value."
        )
    item = array.reshape(-1)[0]
    if isinstance(item, (complex, np.complexfloating)):
        if abs(item.imag) > 1e-9:
            raise AnswerError(f"Submit a real number, got {item}.")
        item = item.real
    try:
        number = float(item)
    except (TypeError, ValueError):
        raise AnswerError(f"Submit a number, got {value!r}.") from None
    if not math.isfinite(number):
        raise AnswerError(f"Submit a finite number, got {number}.")
    return number


def int_dict_answer(values: Any, keys: tuple[str, ...]) -> dict[str, int]:
    """A dictionary of whole numbers with exactly the given keys."""
    if not isinstance(values, Mapping):
        raise AnswerError(f"Submit a dictionary with keys {', '.join(repr(k) for k in keys)}.")
    missing = [key for key in keys if key not in values]
    if missing:
        raise AnswerError(f"Missing answer(s) for {', '.join(repr(k) for k in missing)}.")
    return {key: _as_int(values[key], f"The answer for {key!r}") for key in keys}


def sparse_amplitudes(data: Any) -> tuple[int, list[list[float]]]:
    """Number of qubits and the largest non-zero amplitudes as [index, re, im]."""
    vector = np.asarray(data, dtype=complex).reshape(-1)
    num_qubits = int(round(math.log2(vector.size))) if vector.size else -1
    if vector.size == 0 or 2**num_qubits != vector.size:
        raise AnswerError(f"A statevector needs 2**n amplitudes, got {vector.size}.")
    if not np.all(np.isfinite(vector)):
        raise AnswerError("The statevector contains NaN or infinite amplitudes.")
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        raise AnswerError("The statevector is all zeros.")
    vector = vector / norm
    nonzero = np.flatnonzero(np.abs(vector) > AMPLITUDE_CUTOFF)
    if nonzero.size > MAX_AMPLITUDES:
        order = np.argsort(-np.abs(vector[nonzero]), kind="stable")[:MAX_AMPLITUDES]
        nonzero = np.sort(nonzero[order])
    amps = [[int(i), round(float(vector[i].real), 12), round(float(vector[i].imag), 12)] for i in nonzero]
    return num_qubits, amps


def statevector_answer(state: Any) -> dict[str, Any]:
    """A Statevector (or a measurement-free circuit) as sparse amplitudes."""
    from qiskit import QuantumCircuit

    if isinstance(state, QuantumCircuit):
        return circuit_state_answer(state)
    data = getattr(state, "data", state)
    num_qubits, amps = sparse_amplitudes(data)
    return {"num_qubits": num_qubits, "amps": amps}


def circuit_facts(circuit: Any) -> dict[str, Any]:
    """Qubit count, depth and the qubits of every multi-qubit gate."""
    multi: list[list[int]] = []
    for instruction in circuit.data:
        operation = instruction.operation
        if operation.name in _SKIPPED_OPS or getattr(operation, "_directive", False):
            continue
        if len(instruction.qubits) >= 2 and len(multi) < MAX_GATES:
            multi.append([circuit.find_bit(qubit).index for qubit in instruction.qubits])
    return {"num_qubits": circuit.num_qubits, "depth": circuit.depth(), "multi": multi}


def _without_final_measurements(circuit: Any) -> Any:
    from qiskit import QuantumCircuit

    if not isinstance(circuit, QuantumCircuit):
        raise AnswerError(f"Submit a QuantumCircuit, got {type(circuit).__name__}.")
    return circuit.remove_final_measurements(inplace=False)


def _short_error(err: Exception) -> str:
    return f"{err}"[:300] or type(err).__name__


def circuit_state_answer(circuit: Any) -> dict[str, Any]:
    """Circuit facts plus the sparse statevector of the circuit without final measurements."""
    base = _without_final_measurements(circuit)
    facts = circuit_facts(base)
    if base.num_qubits > MAX_STATEVECTOR_QUBITS:
        return {**facts, "error": f"{base.num_qubits} qubits is too many to simulate a statevector"}
    from qiskit.quantum_info import Statevector

    try:
        data = Statevector(base).data
    except Exception as err:  # noqa: BLE001 - report any simulation failure to the participant
        return {**facts, "error": _short_error(err)}
    _, amps = sparse_amplitudes(data)
    return {**facts, "amps": amps}


def ghz_stabilizer_answer(circuit: Any) -> dict[str, Any]:
    """Circuit facts plus <X...X> and <Z_i Z_i+1> of the circuit's stabilizer state.

    These values identify the GHZ state exactly and scale to circuits far
    beyond statevector simulation. Works for Clifford circuits only.
    """
    base = _without_final_measurements(circuit)
    facts = circuit_facts(base)
    from qiskit.quantum_info import Pauli, StabilizerState

    try:
        state = StabilizerState(base)
    except Exception as err:  # noqa: BLE001 - non-Clifford gates or mid-circuit measurements
        return {**facts, "error": _short_error(err)}
    n = base.num_qubits
    no_x = np.zeros(n, dtype=bool)
    xall = state.expectation_value(Pauli((no_x, np.ones(n, dtype=bool))))
    zz = []
    for i in range(n - 1):
        z = np.zeros(n, dtype=bool)
        z[i] = z[i + 1] = True
        zz.append(int(round(complex(state.expectation_value(Pauli((z, no_x)))).real)))
    return {**facts, "xall": int(round(complex(xall).real)), "zz": zz}
