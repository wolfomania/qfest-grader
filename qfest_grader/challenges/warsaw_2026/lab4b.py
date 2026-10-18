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
# Modified in 2026 by the Qiskit Fall Fest 2026 Warsaw organisers: Warsaw Lab 4b
# grades the exercises of IBM's QGSS 2026 Lab 4c. Every answer is reduced to
# JSON facts on the participant's machine before submission: layout adjacency
# on FakeMiami and the 2-qubit depth of IBM's controlled-phase test circuit,
# outputs of the participant's functions on deterministic test inputs (a greedy
# stand-in generator makes Exercise 3b independent of the NumPy version), and the
# bonus energy recomputed from the submitted subspace and integrals.

"""Qiskit Fall Fest 2026 Warsaw, Lab 4b: grading functions."""

from __future__ import annotations

import hashlib
import random
from collections.abc import Mapping
from functools import lru_cache
from typing import Any, Callable

import numpy as np

from qfest_grader.answers import AnswerError, _as_int
from qfest_grader.facts import call, short_error
from qfest_grader.grade import grade_answer

_LAB = "lab4b"
_NUM_ORBITALS = 26
_TEST_SEED = 2026
_MAX_SUBSPACE = 300
_ENERGY_TOLERANCE = 1e-4
# Integrals from another RHF run differ by an orbital rotation; their spectra agree to about 1e-14.
_INTEGRAL_TOLERANCE = 1e-6
# Controlled-phase angles of IBM's Exercise 1b test circuit (qc_grader qgss_2026 lab4c.py).
_CP_ANGLES = (
    -1.52450963e00, -1.51845886e00, -7.65931488e-01, -2.66798027e-02, -1.51732558e-02, 5.37571952e-02,
    3.61501255e-03, 4.62304337e-02, 1.78404672e-02, 8.64710024e-04, 1.54544066e-02, -3.54207910e-02,
    -3.57567660e-02, 1.64312367e-03, 2.00627775e-02, -3.87242902e-02, -2.46880320e-02, -7.29545064e-03,
    2.91340124e-03, 1.36074778e-02, -4.85994184e-03, -2.85536083e-02, -4.15798626e-02, -7.68232453e-01,
    -1.51392432e00, -1.47923619e00,
)


def _pairs(values: Any, what: str) -> list[tuple[int, int]]:
    if isinstance(values, (str, bytes, Mapping)) or not hasattr(values, "__iter__"):
        raise AnswerError(f"{what} must be a list of (alpha, beta) index pairs.")
    pairs = []
    for pair in values:
        pair = list(pair) if hasattr(pair, "__iter__") and not isinstance(pair, (str, bytes)) else [pair]
        if len(pair) != 2:
            raise AnswerError(f"{what} must contain (alpha, beta) index pairs such as (0, 0), got {pair!r}.")
        pairs.append((_as_int(pair[0], f"An index in {what}"), _as_int(pair[1], f"An index in {what}")))
    return pairs


def _ex1a_answer(alpha_beta_indices: Any) -> dict[str, Any]:
    pairs = _pairs(alpha_beta_indices, "alpha_beta_indices_nh")
    alphas = [p for p, _ in pairs]
    return {
        "count": len(pairs),
        "symmetric": all(p == q for p, q in pairs),
        "start": alphas[0] if alphas else None,
        "steps": sorted({b - a for a, b in zip(alphas, alphas[1:])}),
    }


def grade_lab4b_ex1a(alpha_beta_indices: Any) -> None:
    """Grade Exercise 1a: the alpha-beta interaction pairs for the Nighthawk device."""
    grade_answer(alpha_beta_indices, _LAB, "ex1a", reduce=_ex1a_answer)


def _depth2q(layout: list[int], num_pairs: int, seed: int) -> int:
    """2-qubit depth of IBM's controlled-phase test circuit transpiled on FakeMiami with this layout."""
    from qiskit import QuantumCircuit
    from qiskit.transpiler import generate_preset_pass_manager
    from qiskit_ibm_runtime.fake_provider import FakeMiami

    circuit = QuantumCircuit(2 * _NUM_ORBITALS)
    for i in range(num_pairs):
        circuit.cp(_CP_ANGLES[i], i, i + _NUM_ORBITALS)
    pm = generate_preset_pass_manager(backend=FakeMiami(), optimization_level=1 if num_pairs == 24 else 3,
                                      initial_layout=layout, seed_transpiler=seed)
    return int(pm.run(circuit).depth(filter_function=lambda inst: inst.operation.num_qubits == 2))


def _ex1b_answer(answer: tuple[Any, Any, Any]) -> dict[str, Any]:
    from qiskit_ibm_runtime.fake_provider import FakeMiami

    initial_layout, alpha_beta_indices, seed = answer
    if isinstance(initial_layout, (str, bytes, Mapping)) or not hasattr(initial_layout, "__iter__"):
        raise AnswerError("initial_layout must be the list spin_a_layout + spin_b_layout.")
    layout = [_as_int(q, "A qubit in initial_layout") for q in initial_layout]
    num_pairs = len(_pairs(alpha_beta_indices, "alpha_beta_indices_nh"))
    seed = _TEST_SEED if seed is None else _as_int(seed, "seed")
    backend = FakeMiami()
    edges = {frozenset(edge) for edge in backend.coupling_map.get_edges()}

    def chain(qubits: list[int]) -> bool:
        return len(qubits) == _NUM_ORBITALS and all(frozenset((a, b)) in edges for a, b in zip(qubits, qubits[1:]))

    valid = (len(layout) == 2 * _NUM_ORBITALS and len(set(layout)) == len(layout)
             and all(0 <= q < backend.num_qubits for q in layout))
    depth2q = None
    if valid and 0 < num_pairs <= len(_CP_ANGLES):
        try:
            depth2q = _depth2q(layout, num_pairs, seed)
        except Exception as err:  # noqa: BLE001
            raise AnswerError(f"Transpiling with initial_layout failed ({short_error(err)}).") from None
    return {
        "length": len(layout),
        "distinct": len(set(layout)) == len(layout),
        "in_range": all(0 <= q < backend.num_qubits for q in layout),
        "chain_a": chain(layout[:_NUM_ORBITALS]),
        "chain_b": chain(layout[_NUM_ORBITALS:]),
        "num_pairs": num_pairs,
        "depth2q": depth2q,
    }


def grade_lab4b_ex1b(initial_layout: Any, alpha_beta_indices: Any, seed: Any = None) -> None:
    """Grade Exercise 1b: the Nighthawk qubit layout."""
    grade_answer((initial_layout, alpha_beta_indices, seed), _LAB, "ex1b", reduce=_ex1b_answer)


def make_bits(shape: tuple[int, ...], p: float, seed: int) -> np.ndarray:
    """Deterministic boolean test array; random.Random keeps its stream stable across Python versions."""
    rng = random.Random(seed)
    return np.array([rng.random() < p for _ in range(int(np.prod(shape)))], dtype=bool).reshape(shape)


def make_floats(shape: tuple[int, ...], seed: int) -> np.ndarray:
    rng = random.Random(seed)
    return np.array([rng.random() for _ in range(int(np.prod(shape)))]).reshape(shape)


def _array(value: Any, what: str) -> np.ndarray:
    try:
        return np.asarray(value)
    except Exception as err:  # noqa: BLE001
        raise AnswerError(f"{what} must return a NumPy array ({short_error(err)}).") from None


def _bit_rows(array: np.ndarray) -> list[str]:
    return ["".join("1" if bit else "0" for bit in row.reshape(-1)) for row in array]


def _ex2a_answer(answer: tuple[Any, Any]) -> dict[str, Any]:
    reshape_bitstring, raw_bitstrings = answer
    test = make_bits((25, 12), 0.25, _TEST_SEED)
    output = _array(call(reshape_bitstring, test.copy(), 6, what="reshape_bitstring(test_bitstrings, 6)"),
                    "reshape_bitstring")
    raw = _array(call(reshape_bitstring, np.asarray(raw_bitstrings), _NUM_ORBITALS,
                      what="reshape_bitstring(raw_bitstrings, 26)"), "reshape_bitstring")
    return {
        "test_shape": list(output.shape),
        "test_rows": _bit_rows(output) if output.shape == (25, 2, 6) else None,
        "raw_block_shape": list(raw.shape[1:]),
    }


def grade_lab4b_ex2a(reshape_bitstring: Callable[..., Any], raw_bitstrings: Any) -> None:
    """Grade Exercise 2a: splitting bitstrings into spin sectors."""
    grade_answer((reshape_bitstring, raw_bitstrings), _LAB, "ex2a", reduce=_ex2a_answer)


def _ex2b_answer(hamming_weight: Any) -> dict[str, Any]:
    output = _array(call(hamming_weight, make_bits((25, 2, 6), 0.25, _TEST_SEED + 1), what="hamming_weight"),
                    "hamming_weight")
    return {"shape": list(output.shape),
            "weights": output.astype(int).tolist() if output.shape == (25, 2) else None}


def grade_lab4b_ex2b(hamming_weight: Callable[..., Any]) -> None:
    """Grade Exercise 2b: the Hamming weight per spin sector."""
    grade_answer(hamming_weight, _LAB, "ex2b", reduce=_ex2b_answer)


def _ex3a_answer(weight_flip_0_to_1: Any) -> dict[str, Any]:
    rows = []
    for occupancy in make_floats((10, 24), _TEST_SEED + 2):
        output = _array(call(weight_flip_0_to_1, occupancy, what="weight_flip_0_to_1"), "weight_flip_0_to_1")
        if output.shape != occupancy.shape:
            raise AnswerError(f"weight_flip_0_to_1 must return one weight per orbital, got shape {output.shape}.")
        rows.extend(round(float(x), 9) for x in output)
    return {"values": rows}


def grade_lab4b_ex3a(weight_flip_0_to_1: Callable[..., Any]) -> None:
    """Grade Exercise 3a: the bit-flip weight function."""
    grade_answer(weight_flip_0_to_1, _LAB, "ex3a", reduce=_ex3a_answer)


class GreedyGenerator(np.random.Generator):
    """The rand_seed of Exercise 3b: an np.random.Generator whose choice() returns the most probable items.

    Ties go to the lowest index. np.random.default_rng(rand_seed) returns it unchanged; other methods draw from
    PCG64(seed).
    """

    def __init__(self, seed: int) -> None:
        super().__init__(np.random.PCG64(seed))

    def choice(self, a: Any, size: Any = None, replace: bool = True, p: Any = None, axis: int = 0,
               shuffle: bool = True) -> Any:
        if axis != 0:
            raise ValueError("GreedyGenerator.choice supports axis=0 only")
        items = np.arange(a) if isinstance(a, (int, np.integer)) else np.asarray(a)
        count = 1 if size is None else int(np.prod(size))
        if count == 0:
            return items[np.zeros(size, dtype=int)]
        if len(items) == 0:
            raise ValueError("a cannot be empty unless no samples are taken")
        raw = np.full(len(items), 1 / len(items)) if p is None else np.asarray(p)
        weights = raw.astype(float)
        if weights.shape != (len(items),):
            raise ValueError("a and p must have same size")
        # NumPy's tolerance for the sum of p.
        atol = np.sqrt(np.finfo(np.float64).eps)
        if np.issubdtype(raw.dtype, np.floating):
            atol = max(atol, np.sqrt(np.finfo(raw.dtype).eps))
        if np.any(weights < 0) or not np.isclose(weights.sum(), 1.0, rtol=0, atol=atol):
            raise ValueError("probabilities are not non-negative or do not sum to 1")
        if count > len(items):
            raise ValueError("Cannot take a larger sample than population when replace=False")
        chosen = items[np.argsort(-weights, kind="stable")[:count]]
        return chosen[0] if size is None else chosen.reshape(size)


def recovery_inputs() -> dict[str, Any]:
    """Deterministic Exercise 3b inputs: 50 samples, 12 orbitals, (6, 6) electrons."""
    return {
        "bitstrings": make_bits((50, 2, 12), 0.5, _TEST_SEED + 3),
        "probs": np.full(50, 1 / 50),
        "occupancy": make_floats((2, 12), _TEST_SEED + 4),
        "num_orbitals": 12,
        "num_elec": (6, 6),
    }


def _ex3b_answer(recover_configurations: Any) -> dict[str, Any]:
    inputs = recovery_inputs()
    result = call(recover_configurations, inputs["bitstrings"], inputs["probs"], inputs["occupancy"],
                  inputs["num_orbitals"], inputs["num_elec"], GreedyGenerator(_TEST_SEED),
                  what="recover_configurations")
    try:
        bitstrings, freqs = result
        bitstrings, freqs = np.asarray(bitstrings), np.asarray(freqs, dtype=float).reshape(-1)
        bitstrings = bitstrings.reshape(len(freqs), -1)
    except Exception as err:  # noqa: BLE001
        raise AnswerError(f"recover_configurations must return (bitstrings, probabilities) ({short_error(err)}).") from None
    rows = sorted([row, round(float(f), 9)] for row, f in zip(_bit_rows(bitstrings), freqs))
    half = inputs["num_orbitals"]
    electrons = list(inputs["num_elec"])
    return {
        "valid": all([row[:half].count("1"), row[half:].count("1")] == electrons for row, _ in rows),
        "rows": rows,
    }


def grade_lab4b_ex3b(recover_configurations: Callable[..., Any]) -> None:
    """Grade Exercise 3b: configuration recovery."""
    grade_answer(recover_configurations, _LAB, "ex3b", reduce=_ex3b_answer)


def _digest(values: list[int]) -> str:
    return hashlib.sha256(",".join(map(str, values)).encode()).hexdigest()


def _ex4_answer(hf_like_ci_strings: Any) -> dict[str, Any]:
    array = np.asarray(hf_like_ci_strings)
    facts: dict[str, Any] = {"shape": list(array.shape)}
    if array.ndim != 2 or array.shape[0] != 2:
        return facts
    if not np.issubdtype(array.dtype, np.integer):
        raise AnswerError(f"hf_like_ci_strings must hold integer CI strings, not {array.dtype} values.")
    rows = array.astype(np.int64).tolist()
    facts.update({
        "rows_equal": rows[0] == rows[1],
        "ascending": all(a < b for a, b in zip(rows[0], rows[0][1:])),
        "popcounts": sorted({bin(v).count("1") if v >= 0 else -1 for row in rows for v in row}),
        "set_digest": _digest(sorted(set(rows[0]))),
    })
    return facts


def grade_lab4b_ex4(hf_like_ci_strings: Any) -> None:
    """Grade Exercise 4: the HF-like CI strings."""
    grade_answer(hf_like_ci_strings, _LAB, "ex4", reduce=_ex4_answer)


@lru_cache(maxsize=1)
def _n2_hamiltonian() -> tuple[Any, Any, float, int, tuple[int, int]]:
    """Active-space integrals of N2 (cc-pVDZ, 2.0 Å, 2 frozen orbitals), as notebook cell 9 builds them."""
    import pyscf
    import pyscf.mcscf

    mol = pyscf.gto.Mole()
    mol.build(atom=[["N", (0, 0, 0)], ["N", (2.0, 0, 0)]], basis="cc-pvdz", verbose=0)
    active_space = range(2, mol.nao_nr())
    scf = pyscf.scf.RHF(mol).run()
    num_orbitals = len(active_space)
    n_electrons = int(sum(scf.mo_occ[active_space]))
    nelec = ((n_electrons + mol.spin) // 2, (n_electrons - mol.spin) // 2)
    cas = pyscf.mcscf.CASCI(scf, num_orbitals, nelec)
    mo = cas.sort_mo(active_space, base=0)
    hcore, core_energy = cas.get_h1cas(mo)
    eri = pyscf.ao2mo.restore(1, cas.get_h2cas(mo), num_orbitals)
    return hcore, eri, float(core_energy), num_orbitals, nelec


def _ci_strings(values: Any, what: str) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1 or not np.issubdtype(array.dtype, np.integer):
        raise AnswerError(f"{what} must be a 1-D integer array of CI strings.")
    return array.astype(np.int64)


def _integrals(hcore: Any, eri: Any, nuclear_repulsion_energy: Any) -> tuple[np.ndarray, np.ndarray, float]:
    """The submitted integrals, checked to be the N2 integrals up to an orbital rotation.

    Every RHF run may rotate the degenerate pi orbitals differently, so CI strings mean something only in the basis of
    the integrals they were sampled with. A rotation u keeps the spectra of hcore, of eri as a matrix and of
    eri + hcore x 1 + 1 x hcore; the last one fails when hcore and eri come from different rotations.
    """
    ref_hcore, ref_eri, ref_core, n, _ = _n2_hamiltonian()
    try:
        h, g, core = np.asarray(hcore, dtype=float), np.asarray(eri, dtype=float), float(nuclear_repulsion_energy)
    except (TypeError, ValueError):
        h = g = None
    if (h is None or h.shape != (n, n) or g.shape != (n,) * 4 or not np.all(np.isfinite(h))
            or not np.all(np.isfinite(g))):
        raise AnswerError(f"Pass hcore ({n} x {n}), eri ({n} x {n} x {n} x {n}) and nuclear_repulsion_energy from the "
                          "cell that builds the N2 Hamiltonian.")

    def spectra(one_body: np.ndarray, two_body: np.ndarray) -> list[np.ndarray]:
        eye, pairs = np.eye(n), two_body.reshape(n * n, n * n)
        matrices = (one_body, pairs, pairs + np.kron(one_body, eye) + np.kron(eye, one_body))
        return [np.linalg.eigvalsh((m + m.T) / 2) for m in matrices]

    if not (abs(core - ref_core) <= _INTEGRAL_TOLERANCE
            and all(np.allclose(mine, ref, rtol=0, atol=_INTEGRAL_TOLERANCE)
                    for mine, ref in zip(spectra(h, g), spectra(ref_hcore, ref_eri)))):
        raise AnswerError("hcore, eri and nuclear_repulsion_energy are not the N2 integrals of this lab. Pass the ones "
                          "from the cell that builds the N2 Hamiltonian.")
    return h, g, core


def _exbonus_answer(answer: tuple[Any, Any, Any, Any, Any]) -> dict[str, Any]:
    best_energy, best_subspace, hcore, eri, nuclear_repulsion_energy = answer
    try:
        claimed = float(best_energy)
        strings_a, strings_b = best_subspace
    except (TypeError, ValueError):
        raise AnswerError("Submit best_energy as a number and best_subspace as (ci_strs_a, ci_strs_b).") from None
    strings_a = _ci_strings(strings_a, "best_subspace[0]")
    strings_b = _ci_strings(strings_b, "best_subspace[1]")
    facts: dict[str, Any] = {"dims": [len(strings_a), len(strings_b)], "energy": None, "matches": False}
    if min(facts["dims"]) == 0 or max(facts["dims"]) > _MAX_SUBSPACE:
        return facts
    from qiskit_addon_sqd.fermion import solve_sci

    *_, num_orbitals, nelec = _n2_hamiltonian()
    h, g, core = _integrals(hcore, eri, nuclear_repulsion_energy)
    for i, strings in enumerate((strings_a, strings_b)):
        if np.any(np.diff(strings) <= 0):
            raise AnswerError(f"best_subspace[{i}] must hold distinct CI strings in ascending order (np.unique).")
        if np.any(strings < 0) or np.any(strings >= 1 << num_orbitals) or any(
                bin(int(s)).count("1") != nelec[i] for s in strings):
            raise AnswerError(f"Every CI string in best_subspace[{i}] must have {nelec[i]} of the {num_orbitals} "
                              "orbitals occupied.")
    print("Recomputing the energy of best_subspace (up to two minutes)...")
    try:
        energy = solve_sci((strings_a, strings_b), h, g, num_orbitals, nelec).energy + core
    except Exception as err:  # noqa: BLE001
        raise AnswerError(f"Could not diagonalize best_subspace ({short_error(err)}).") from None
    facts["energy"] = round(float(energy), 6)
    # A spin-constrained solver (spin_sq=0.0) reports an energy above the lowest one of the subspace, never below.
    facts["matches"] = claimed >= float(energy) - _ENERGY_TOLERANCE
    return facts


def grade_lab4b_exbonus(best_energy: Any, best_subspace: Any, hcore: Any, eri: Any,
                        nuclear_repulsion_energy: Any) -> None:
    """Grade the bonus: the N2 energy of best_subspace, recomputed here with your integrals; scored by tiers."""
    grade_answer((best_energy, best_subspace, hcore, eri, nuclear_repulsion_energy), _LAB, "exbonus",
                 reduce=_exbonus_answer)
