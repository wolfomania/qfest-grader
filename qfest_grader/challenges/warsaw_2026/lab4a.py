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
# Modified in 2026 by the Qiskit Fall Fest 2026 Warsaw organisers: Warsaw Lab 4a
# grades the exercises of IBM's QGSS 2026 Lab 4b. Every answer is reduced to
# JSON facts on the participant's machine (graph edges, Pauli terms, states at
# fixed parameters, a comparison of circuit_pce with the QAOA ansatz of the
# submitted Hamiltonian, options values, partition differences) before submission. Jobs are read only to compare their expectation values with
# the submitted ones; simulator jobs are accepted.

"""Qiskit Fall Fest 2026 Warsaw, Lab 4a: grading functions."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from typing import Any, Callable

import numpy as np

from qfest_grader.answers import AnswerError, _as_int, circuit_state_answer
from qfest_grader.facts import call, int_list, require_circuit, short_error, unroll_boxes
from qfest_grader.grade import grade_answer
from qfest_grader.options import option_value, plain
from qfest_grader.paulis import observable_facts, sparse_terms

_LAB = "lab4a"
# The numbers of section 1 (notebook cell 17).
_SMALL_NUMBERS = (3, 5, 7, 9, 11, 13)
_PCE_SIZES = tuple(range(20, 201, 20))
# Bound to the circuit parameters in sorted-name order before states and expectation values are computed.
_FIXED_PARAMETERS = (0.37, 0.61, 0.83, 1.19, 0.29, 0.71, 1.07, 0.53)
_METHODS = ("No EM", "TREX", "ZNE", "PEC")
_MAX_GRAPH_EDGES = 500
_MAX_PCE_OPS = 500
_MAX_STATE_QUBITS = 16
_PCE_REPS = 2
_SAMPLER_FIELDS = {
    "default_shots": "default_shots",
    "dd_enable": "dynamical_decoupling.enable",
    "dd_sequence": "dynamical_decoupling.sequence_type",
    "twirl_gates": "twirling.enable_gates",
    "twirl_measure": "twirling.enable_measure",
    "randomizations": "twirling.num_randomizations",
}
_ESTIMATOR_FIELDS = {
    "default_shots": "default_shots",
    "resilience_level": "resilience_level",
    "measure_mitigation": "resilience.measure_mitigation",
    "zne_mitigation": "resilience.zne_mitigation",
    "pec_mitigation": "resilience.pec_mitigation",
    "twirl_gates": "twirling.enable_gates",
    "twirl_measure": "twirling.enable_measure",
}


def _items(values: Any, what: str) -> list[Any]:
    if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, (list, tuple)):
        raise AnswerError(f"{what} must be a list, got {type(values).__name__}.")
    return list(values)


def _graph_facts(graph: Any, what: str) -> dict[str, Any]:
    try:
        nodes = sorted(_as_int(node, f"A node of {what}") for node in graph.nodes())
        raw_edges = list(graph.edges(data="weight"))
    except AnswerError:
        raise
    except Exception as err:  # noqa: BLE001
        raise AnswerError(f"{what} must be a networkx Graph ({short_error(err)}).") from None
    if len(raw_edges) > _MAX_GRAPH_EDGES:
        raise AnswerError(f"{what} has {len(raw_edges)} edges, far more than expected.")
    edges = []
    for u, v, weight in raw_edges:
        a, b = _as_int(u, f"A node of {what}"), _as_int(v, f"A node of {what}")
        edges.append([min(a, b), max(a, b), plain(weight)])
    return {"nodes": nodes, "num_edges": len(edges), "edges": sorted(edges, key=lambda e: (e[0], e[1]))}


def grade_lab4a_ex1a(partition_graph: Any) -> None:
    """Grade Exercise 1a: the partition graph of the 6 numbers."""
    grade_answer(partition_graph, _LAB, "ex1a", reduce=lambda graph: _graph_facts(graph, "partition_graph"))


def _bound_circuit(circuit: Any, what: str) -> tuple[Any, Any]:
    """The circuit with boxes unrolled, and the same circuit with the fixed parameter values bound."""
    unrolled = unroll_boxes(require_circuit(circuit, what))
    params = list(unrolled.parameters)
    if len(params) > len(_FIXED_PARAMETERS):
        raise AnswerError(f"{what} has {len(params)} parameters, far more than expected.")
    return unrolled, unrolled.assign_parameters(dict(zip(params, _FIXED_PARAMETERS)))


def _ex1b_answer(answer: tuple[Any, Any]) -> dict[str, Any]:
    hamiltonian, circuit = answer
    facts = observable_facts(hamiltonian, "partition_hamiltonian")
    unrolled, bound = _bound_circuit(circuit, "circuit")
    return {
        "hamiltonian": facts,
        "qubits": unrolled.num_qubits,
        "num_parameters": unrolled.num_parameters,
        "state": circuit_state_answer(bound),
    }


def grade_lab4a_ex1b(partition_hamiltonian: Any, circuit: Any) -> None:
    """Grade Exercise 1b: the partition Hamiltonian and its QAOA circuit."""
    grade_answer((partition_hamiltonian, circuit), _LAB, "ex1b", reduce=_ex1b_answer)


def _sampler_facts(options: Any, what: str) -> dict[str, Any]:
    return {key: option_value(options, path, f"{what}.{path}") for key, path in _SAMPLER_FIELDS.items()}


def grade_lab4a_ex2a(options_v1: Any) -> None:
    """Grade Exercise 2a: SamplerOptions without error mitigation or suppression."""
    grade_answer(options_v1, _LAB, "ex2a", reduce=lambda options: _sampler_facts(options, "options_v1"))


def grade_lab4a_ex2b(options_v2: Any) -> None:
    """Grade Exercise 2b: SamplerOptions with dynamical decoupling and twirling."""
    grade_answer(options_v2, _LAB, "ex2b", reduce=lambda options: _sampler_facts(options, "options_v2"))


def _measurement_map(circuit: Any) -> dict[int, int]:
    """{clbit: qubit} of the last measurement into each classical bit."""
    mapping = {}
    for inst in circuit.data:
        if inst.operation.name == "measure":
            mapping[circuit.find_bit(inst.clbits[0]).index] = circuit.find_bit(inst.qubits[0]).index
    return mapping


def _meas_map(value: Any, what: str) -> dict[int, int]:
    if isinstance(value, Mapping):
        return {_as_int(k, f"A key of {what}"): _as_int(v, f"A value of {what}") for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return {i: _as_int(q, f"An entry of {what}") for i, q in enumerate(value)}
    raise AnswerError(f"{what} must be the mapping from mthree.utils.final_measurement_mapping.")


def _distribution_facts(dist: Any, what: str) -> dict[str, Any]:
    if not isinstance(dist, Mapping):
        raise AnswerError(f"{what} must be a dictionary of bitstrings, got {type(dist).__name__}.")
    try:
        total = sum(float(value) for value in dist.values())
    except (TypeError, ValueError):
        raise AnswerError(f"{what} must map bitstrings to numbers.") from None
    return {
        "keys": len(dist),
        "key_bits": sorted({len(key) if isinstance(key, str) else -1 for key in dist}),
        "total": round(total, 9),
    }


def _m3_answer(answer: tuple[Any, Any, Any, Any, Any], label: str) -> dict[str, Any]:
    options, circuit, meas_map, quasis, counts = answer
    circuit = require_circuit(circuit, "optimized_circuit")
    return {
        "options": _sampler_facts(options, f"options_{label}"),
        "meas_map_matches": _meas_map(meas_map, f"meas_map_{label}") == _measurement_map(circuit),
        "quasis": _distribution_facts(quasis, f"m3_quasis_{label}"),
        "counts": _distribution_facts(counts, f"counts_bin_{label}"),
    }


def grade_lab4a_ex2c(options_v3: Any, optimized_circuit: Any, meas_map_v3: Any, m3_quasis_v3: Any,
                     counts_bin_v3: Any) -> None:
    """Grade Exercise 2c: M3 readout mitigation of the unsuppressed run."""
    grade_answer((options_v3, optimized_circuit, meas_map_v3, m3_quasis_v3, counts_bin_v3), _LAB, "ex2c",
                 reduce=lambda answer: _m3_answer(answer, "v3"))


def grade_lab4a_ex2d(options_v4: Any, optimized_circuit: Any, meas_map_v4: Any, m3_quasis_v4: Any,
                     counts_bin_v4: Any) -> None:
    """Grade Exercise 2d: M3 readout mitigation of the suppressed run."""
    grade_answer((options_v4, optimized_circuit, meas_map_v4, m3_quasis_v4, counts_bin_v4), _LAB, "ex2d",
                 reduce=lambda answer: _m3_answer(answer, "v4"))


def _most_likely_difference(dist: Any, what: str) -> int | None:
    """Partition difference of the most likely bitstring, as analyze_partition_result computes it."""
    if not isinstance(dist, Mapping):
        raise AnswerError(f"{what} must be a dictionary of bitstrings, got {type(dist).__name__}.")
    if not dist:
        return None
    keys = list(dist)
    weights = [abs(float(value)) for value in dist.values()]
    best = keys[weights.index(max(weights))]
    if not isinstance(best, str) or len(best) != len(_SMALL_NUMBERS) or set(best) - {"0", "1"}:
        raise AnswerError(f"{what} must have {len(_SMALL_NUMBERS)}-bit string keys such as '000111', got {best!r}.")
    in_set = sum(n for n, bit in zip(_SMALL_NUMBERS, reversed(best)) if bit == "1")
    return abs(2 * in_set - sum(_SMALL_NUMBERS))


def _ex2_answer(answer: tuple[Any, Any, Any]) -> dict[str, Any]:
    options_list, probs_list, _ = answer
    dists = _items(probs_list, "probs_list")
    differences = [_most_likely_difference(dist, f"probs_list[{i}]") for i, dist in enumerate(dists)]
    found = [d for d in differences if d is not None]
    return {
        "options": [_sampler_facts(o, f"options_list[{i}]") for i, o in enumerate(_items(options_list, "options_list"))],
        "sizes": [len(dist) for dist in dists],
        "best_difference": min(found) if found else None,
    }


def grade_lab4a_ex2(options_list: Any, probs_list: Any, job_list: Any) -> None:
    """Grade Exercise 2: the four Sampler configurations and their distributions."""
    grade_answer((options_list, probs_list, job_list), _LAB, "ex2", reduce=_ex2_answer)


def _ex3a_answer(answer: tuple[Callable[[int], Any], Any, Any, Any]) -> dict[str, Any]:
    reduce_fn, node_x, node_y, node_z = answer
    return {
        "final_qubits": [
            _as_int(call(reduce_fn, n, what=f"reduce_qubits_with_pce({n})"), f"reduce_qubits_with_pce({n})")
            for n in _PCE_SIZES
        ],
        "node_x": int_list(node_x, "node_x"),
        "node_y": int_list(node_y, "node_y"),
        "node_z": int_list(node_z, "node_z"),
    }


def grade_lab4a_ex3a(reduce_qubits_with_pce: Any, node_x: Any, node_y: Any, node_z: Any) -> None:
    """Grade Exercise 3a: PCE qubit reduction and the node lists."""
    grade_answer((reduce_qubits_with_pce, node_x, node_y, node_z), _LAB, "ex3a", reduce=_ex3a_answer)


def _pce_ops(ops: Any, what: str) -> list[dict[str, Any]]:
    items = _items(ops, what)
    if len(items) > _MAX_PCE_OPS:
        raise AnswerError(f"{what} has {len(items)} operators, far more than expected.")
    return [
        {"qubits": int(getattr(op, "num_qubits", -1)), "terms": sparse_terms(op, f"{what}[{i}]")}
        for i, op in enumerate(items)
    ]


def _ex3b_answer(answer: tuple[Any, Any, Any]) -> dict[str, Any]:
    names = ("pauli_correlation_encoding_x", "pauli_correlation_encoding_y", "pauli_correlation_encoding_z")
    return {axis: _pce_ops(ops, name) for axis, ops, name in zip("xyz", answer, names)}


def grade_lab4a_ex3b(pauli_correlation_encoding_x: Any, pauli_correlation_encoding_y: Any,
                     pauli_correlation_encoding_z: Any) -> None:
    """Grade Exercise 3b: the 2-body Pauli correlation terms."""
    grade_answer((pauli_correlation_encoding_x, pauli_correlation_encoding_y, pauli_correlation_encoding_z),
                 _LAB, "ex3b", reduce=_ex3b_answer)


def _own_ansatz(hamiltonian: Any, bound: Any) -> bool:
    """Whether the bound circuit has the state of annotated_qaoa_ansatz(hamiltonian, reps=2) at the fixed values.

    The XX, YY and ZZ terms do not commute, so the ansatz depends on the term order of the submitted Hamiltonian.
    PauliEvolution gates (flatten=False) are simulated as their Lie-Trotter circuits, which flatten=True builds.
    """
    try:
        from qopt_best_practices.circuit_library import annotated_qaoa_ansatz
    except ImportError:
        raise AnswerError("grade_lab4a_ex3c needs qopt_best_practices: install it and run the Imports cell.") from None
    from qiskit.quantum_info import Statevector

    def state(circuit: Any) -> Statevector:
        return Statevector(circuit.remove_final_measurements(inplace=False).decompose(
            gates_to_decompose=["PauliEvolution"]))

    try:
        _, expected = _bound_circuit(annotated_qaoa_ansatz(hamiltonian, reps=_PCE_REPS), "the QAOA ansatz")
        overlap = state(expected).inner(state(bound))
    except Exception:  # noqa: BLE001 - reported as a mismatch
        return False
    return bool(abs(overlap) ** 2 > 1 - 1e-6)


def _ex3c_answer(answer: tuple[Any, Any]) -> dict[str, Any]:
    hamiltonian, circuit = answer
    facts = observable_facts(hamiltonian, "hamiltonian_pce")
    unrolled, bound = _bound_circuit(circuit, "circuit_pce")
    comparable = bound.num_qubits == facts["qubits"] <= _MAX_STATE_QUBITS
    return {
        "hamiltonian": facts,
        "qubits": unrolled.num_qubits,
        "num_parameters": unrolled.num_parameters,
        "own_ansatz": _own_ansatz(hamiltonian, bound) if comparable else None,
    }


def grade_lab4a_ex3c(hamiltonian_pce: Any, circuit_pce: Any) -> None:
    """Grade Exercise 3c: the PCE cost Hamiltonian and its QAOA circuit."""
    grade_answer((hamiltonian_pce, circuit_pce), _LAB, "ex3c", reduce=_ex3c_answer)


def _estimator_facts(options: Any, what: str) -> dict[str, Any]:
    return {key: option_value(options, path, f"{what}.{path}") for key, path in _ESTIMATOR_FIELDS.items()}


def grade_lab4a_ex4a(est_options_no_em: Any) -> None:
    """Grade Exercise 4a: EstimatorOptions without error mitigation."""
    grade_answer(est_options_no_em, _LAB, "ex4a", reduce=lambda o: _estimator_facts(o, "est_options_no_em"))


def grade_lab4a_ex4b(est_options_trex: Any) -> None:
    """Grade Exercise 4b: EstimatorOptions with TREX and twirling."""
    grade_answer(est_options_trex, _LAB, "ex4b", reduce=lambda o: _estimator_facts(o, "est_options_trex"))


def grade_lab4a_ex4c(est_options_zne: Any) -> None:
    """Grade Exercise 4c: EstimatorOptions with ZNE and twirling."""
    grade_answer(est_options_zne, _LAB, "ex4c", reduce=lambda o: _estimator_facts(o, "est_options_zne"))


def grade_lab4a_ex4d(est_options_pec: Any) -> None:
    """Grade Exercise 4d: EstimatorOptions with PEC and twirling."""
    grade_answer(est_options_pec, _LAB, "ex4d", reduce=lambda o: _estimator_facts(o, "est_options_pec"))


def _job_exp_map(job: Any, what: str) -> dict[int, float]:
    """{index: <P>} over all PUB results of an Estimator job, as the notebook's loss function builds it."""
    try:
        result = job.result()
    except Exception as err:  # noqa: BLE001
        raise AnswerError(f"Could not read the result of {what} ({short_error(err)}).") from None
    values: dict[int, float] = {}
    for pub in result:
        for ev in np.asarray(getattr(getattr(pub, "data", None), "evs", [])).reshape(-1):
            values[len(values)] = float(ev)
    return values


def _exp_map_matches(stored: Any, job: Any, what: str) -> bool:
    if not isinstance(stored, Mapping):
        return False
    expected = _job_exp_map(job, what)
    try:
        got = {int(key): float(value) for key, value in stored.items()}
    except (TypeError, ValueError):
        return False
    return got.keys() == expected.keys() and all(
        math.isclose(got[key], expected[key], rel_tol=1e-9, abs_tol=1e-12) for key in got
    )


def _numbers_digest(values: list[int]) -> str:
    """SHA-256 of the sorted numbers; equal digests mean equal multisets."""
    return hashlib.sha256(",".join(map(str, sorted(values))).encode()).hexdigest()


def _partition_sets(entry: Any, what: str) -> tuple[list[int], list[int]]:
    if not isinstance(entry, Mapping):
        raise AnswerError(f"{what} must be a partition result dictionary with 'set0' and 'set1'.")
    return (int_list(entry.get("set0", ()), f"{what}['set0']"), int_list(entry.get("set1", ()), f"{what}['set1']"))


def _method_facts(entry: Any, job: Any, what: str) -> dict[str, Any]:
    set0, set1 = _partition_sets(entry, what)
    return {
        "difference": abs(sum(set0) - sum(set1)),
        "count": len(set0) + len(set1),
        "numbers": _numbers_digest(set0 + set1),
        "exp_map_matches": _exp_map_matches(entry.get("exp_map"), job, f"the {what} job"),
    }


def _ex4_answer(answer: tuple[Any, Any, Any]) -> dict[str, Any]:
    options_list, results, jobs = answer
    if not isinstance(results, Mapping) or set(results) != set(_METHODS):
        raise AnswerError(f"results must have exactly the keys {list(_METHODS)}.")
    jobs = _items(jobs, "jobs_est_list")
    if len(jobs) != len(_METHODS):
        raise AnswerError(f"jobs_est_list must hold {len(_METHODS)} jobs, in the order {', '.join(_METHODS)}.")
    methods = {name: _method_facts(results[name], job, f"results['{name}']") for name, job in zip(_METHODS, jobs)}
    best = min(_METHODS, key=lambda name: methods[name]["difference"])
    return {
        "options": [_estimator_facts(o, f"estimator_options_list[{i}]")
                    for i, o in enumerate(_items(options_list, "estimator_options_list"))],
        "methods": methods,
        "best_method": best,
        "best_difference": methods[best]["difference"],
    }


def grade_lab4a_ex4(estimator_options_list: Any, results: Any, jobs_est_list: Any) -> None:
    """Grade Exercise 4: the four Estimator configurations and their partitions."""
    grade_answer((estimator_options_list, results, jobs_est_list), _LAB, "ex4", reduce=_ex4_answer)


def _bools_as_ints(values: Any) -> Any:
    """True and False as 1 and 0, as best_bits[i] == 1 reads them."""
    if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, (list, tuple, np.ndarray)):
        return values
    return [int(value) if isinstance(value, (bool, np.bool_)) else value for value in values]


def _exbonus_answer(answer: tuple[Any, Any, Any, Any]) -> dict[str, Any]:
    result, best_bits, numbers_bonus, job = answer
    numbers = int_list(numbers_bonus, "numbers_bonus")
    bits = int_list(_bools_as_ints(best_bits), "best_bits")
    if len(bits) != len(numbers):
        raise AnswerError("best_bits must hold one bit per number in numbers_bonus.")
    set0 = [n for n, bit in zip(numbers, bits) if bit == 1]
    set1 = [n for n, bit in zip(numbers, bits) if bit == 0]
    stored0, stored1 = _partition_sets(result, "result_bonus")
    return {
        "count": len(numbers),
        "numbers": _numbers_digest(numbers),
        "bits_valid": set(bits) <= {0, 1},
        "bits_match": (stored0, stored1) == (set0, set1),
        "exp_map_matches": _exp_map_matches(result.get("exp_map"), job, "job_bonus"),
        "hardware_job": type(job).__name__ == "RuntimeJobV2",
        "difference": abs(sum(set0) - sum(set1)),
    }


def grade_lab4a_exbonus(result_bonus: Any, best_bits: Any, numbers_bonus: Any, job_bonus: Any) -> None:
    """Grade the bonus: the 1600-number partition; scored by its difference."""
    grade_answer((result_bonus, best_bits, numbers_bonus, job_bonus), _LAB, "exbonus", reduce=_exbonus_answer)
