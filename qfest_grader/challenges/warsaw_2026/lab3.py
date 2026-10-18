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
# Modified in 2026 by the Qiskit Fall Fest 2026 Warsaw organisers: every answer
# is reduced to JSON facts on the participant's machine (options values,
# circuit and box counts, observable terms, bound sizes) before submission;
# samplomatic and the add-ons are imported only when a grade function runs.

"""Qiskit Fall Fest 2026 Warsaw, Lab 3: grading functions."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from qfest_grader.answers import AnswerError
from qfest_grader.facts import count_ops, require_circuit, short_error
from qfest_grader.grade import grade_answer
from qfest_grader.options import option_value
from qfest_grader.paulis import observable_facts, sparse_terms

_LAB = "lab3"
_PI_8 = math.pi / 8
_OPTION_KEYS = ("dd", "pt", "trex", "zne", "pec")
_OPTION_FIELDS = {
    "dd": {"enable": "dynamical_decoupling.enable", "sequence_type": "dynamical_decoupling.sequence_type"},
    "pt": {
        "enable_gates": "twirling.enable_gates",
        "strategy": "twirling.strategy",
        "num_randomizations": "twirling.num_randomizations",
    },
    "trex": {"measure_mitigation": "resilience.measure_mitigation"},
    "zne": {
        "zne_mitigation": "resilience.zne_mitigation",
        "noise_factors": "resilience.zne.noise_factors",
        "amplifier": "resilience.zne.amplifier",
    },
    "pec": {"pec_mitigation": "resilience.pec_mitigation", "max_overhead": "resilience.pec.max_overhead"},
}
_MAX_STATEVECTOR_QUBITS = 20


def _ex1_answer(options_dict: Any) -> dict[str, Any]:
    if not isinstance(options_dict, Mapping) or set(options_dict) != set(_OPTION_KEYS):
        raise AnswerError(f"Submit a dictionary with exactly the keys {list(_OPTION_KEYS)}.")
    return {
        key: {field: option_value(options_dict[key], path, f"{key}.{path}") for field, path in fields.items()}
        for key, fields in _OPTION_FIELDS.items()
    }


def grade_lab3_ex1(options_dict: Any) -> None:
    """Grade Exercise 1: five EstimatorOptions, one per error-mitigation method."""
    grade_answer(options_dict, _LAB, "ex1", reduce=_ex1_answer)


def _zero_state_fidelity(circuit: Any) -> float:
    """|<0...0|circuit>|^2 of the circuit without its final measurements; 0 if it cannot be simulated."""
    from qiskit.quantum_info import Statevector

    base = circuit.remove_final_measurements(inplace=False)
    if base.num_qubits > _MAX_STATEVECTOR_QUBITS:
        return 0.0
    try:
        return round(float(abs(Statevector(base).data[0]) ** 2), 9)
    except Exception:  # noqa: BLE001 - mid-circuit operations or unsupported gates
        return 0.0


def _ising_facts(circuit: Any) -> dict[str, Any]:
    ops = count_ops(circuit)
    rx_angles = []
    for inst in circuit.data:
        if inst.operation.name == "rx":
            try:
                rx_angles.append(float(inst.operation.params[0]))
            except (TypeError, ValueError):
                rx_angles.append(float("nan"))
    return {
        "qubits": circuit.num_qubits,
        "ops": {name: count for name, count in ops.items() if name != "barrier"},
        "barriers": ops.get("barrier", 0),
        "rx_all_pi8": bool(rx_angles) and all(abs(a - _PI_8) < 1e-9 for a in rx_angles),
    }


def _mirror_facts(circuit: Any) -> dict[str, Any]:
    ops = count_ops(circuit)
    return {
        "qubits": circuit.num_qubits,
        "ops": {name: count for name, count in ops.items() if name not in ("barrier", "measure")},
        "measures": ops.get("measure", 0),
        "zero_fidelity": _zero_state_fidelity(circuit),
    }


def _box_facts(boxed: Any) -> dict[str, Any]:
    from qiskit.circuit import BoxOp

    boxes = [inst.operation for inst in boxed.data if isinstance(inst.operation, BoxOp)]

    def has_measure(box: Any) -> bool:
        return any(sub.operation.name == "measure" for sub in box.body.data)

    def annotated(box: Any, kind: str) -> bool:
        return any(type(annotation).__name__ == kind for annotation in getattr(box, "annotations", ()))

    gate_boxes = [box for box in boxes if not has_measure(box)]
    return {
        "boxes": len(boxes),
        "gate_boxes": len(gate_boxes),
        "gate_boxes_twirl": sum(annotated(box, "Twirl") for box in gate_boxes),
        "gate_boxes_inject": sum(annotated(box, "InjectNoise") for box in gate_boxes),
    }


def _ex2_answer(answer: tuple[Any, Any, Any]) -> dict[str, Any]:
    ising, mirror, boxed = (require_circuit(c, name) for c, name in zip(answer, ("ising_ex2", "mirror_ex2", "boxed_circuit_ex2")))
    facts: dict[str, Any] = {"ising": _ising_facts(ising), "mirror": _mirror_facts(mirror), "boxed": _box_facts(boxed)}
    build_error = None
    if facts["boxed"]["boxes"]:
        try:
            import samplomatic

            samplomatic.build(boxed)
        except Exception as err:  # noqa: BLE001 - reported to the participant by the server message
            build_error = short_error(err)
    facts["boxed"]["build_ok"] = bool(facts["boxed"]["boxes"]) and build_error is None
    facts["boxed"]["build_error"] = build_error
    return facts


def grade_lab3_ex2(ising_ex2: Any, mirror_ex2: Any, boxed_circuit_ex2: Any) -> None:
    """Grade Exercise 2: the 6-qubit Ising circuit, its mirror and the boxed mirror."""
    grade_answer((ising_ex2, mirror_ex2, boxed_circuit_ex2), _LAB, "ex2", reduce=_ex2_answer)


def _ex3_answer(answer: tuple[Any, Any, Any, Any, Any]) -> dict[str, Any]:
    template, samplex, samplex_args, program, noise_models = answer
    template = require_circuit(template, "template_ex3")
    if not isinstance(noise_models, Mapping):
        raise AnswerError("refs_to_noise_models_ex3 must be the {ref: PauliLindbladMap} dictionary from the noise learner.")
    try:
        samplex_refs = sorted(str(spec.name) for spec in samplex.inputs().get_specs())
    except Exception as err:  # noqa: BLE001
        raise AnswerError(f"samplex_ex3 is not a samplex from samplomatic.build ({short_error(err)}).") from None
    try:
        fully_bound = bool(samplex_args.fully_bound)
    except Exception as err:  # noqa: BLE001
        raise AnswerError(f"samplex_args_ex3 is not a bound samplex input ({short_error(err)}).") from None
    try:
        items = list(program.items)
    except Exception as err:  # noqa: BLE001
        raise AnswerError(f"program_ex3 is not a QuantumProgram ({short_error(err)}).") from None
    noise_keys = sorted(f"pauli_lindblad_maps.{key}" for key in noise_models)
    item = items[0] if items else None
    noise_slots = [ref for ref in samplex_refs if ref.startswith("pauli_lindblad_maps.")]
    return {
        "template_params": int(template.num_parameters),
        "noise_slots": len(noise_slots),
        "noise_keys": len(noise_keys),
        "slots_match_noise": noise_slots == noise_keys,
        "args_fully_bound": fully_bound,
        "num_items": len(items),
        "item_circuit_matches": item is not None and getattr(item, "circuit", None) is template,
        "item_samplex_matches": item is not None and getattr(item, "samplex", None) is samplex,
    }


def grade_lab3_ex3(
    template_ex3: Any,
    samplex_ex3: Any,
    samplex_args_ex3: Any,
    program_ex3: Any,
    refs_to_noise_models_ex3: Any,
) -> None:
    """Grade Exercise 3: template, samplex, bound noise models and the QuantumProgram."""
    grade_answer(
        (template_ex3, samplex_ex3, samplex_args_ex3, program_ex3, refs_to_noise_models_ex3),
        _LAB,
        "ex3",
        reduce=_ex3_answer,
    )


def _ex4_answer(answer: tuple[Any, Any, Any]) -> dict[str, Any]:
    target, target_isa, obs_tilde = answer
    return {
        "target": observable_facts(target, "target_observable_ex4"),
        "target_isa": observable_facts(target_isa, "target_observable_ex4_isa"),
        "obs_tilde": observable_facts(obs_tilde, "obs_tilde_ex4", top=10),
    }


def grade_lab3_ex4(target_observable_ex4: Any, target_observable_ex4_isa: Any, obs_tilde_ex4: Any) -> None:
    """Grade Exercise 4: the 10-qubit target observable, its ISA layout and the PNA observable."""
    grade_answer((target_observable_ex4, target_observable_ex4_isa, obs_tilde_ex4), _LAB, "ex4", reduce=_ex4_answer)


def _bound_facts(bounds: Any, what: str) -> dict[str, Any]:
    """Size and sanity of a {ref: PauliLindbladMap} bounds dictionary."""
    if not isinstance(bounds, Mapping):
        raise AnswerError(f"{what} must be a dictionary of PauliLindbladMap bounds, got {type(bounds).__name__}.")
    terms, finite = 0, True
    for value in bounds.values():
        try:
            sparse = value.to_sparse_list()
        except Exception as err:  # noqa: BLE001
            raise AnswerError(f"{what} must contain PauliLindbladMap values ({short_error(err)}).") from None
        terms += len(sparse)
        finite = finite and all(math.isfinite(float(rate)) and float(rate) >= 0 for *_, rate in sparse)
    return {"keys": len(bounds), "terms": terms, "finite_nonneg": finite}


def _ex5_answer(answer: tuple[Any, Any, Any, Any, Any, Any]) -> dict[str, Any]:
    circuit_ising, mirrored, boxed, obs_list, forward_list, backward = answer
    circuit_ising = require_circuit(circuit_ising, "circuit_ising")
    mirrored = require_circuit(mirrored, "mirrored_circuit")
    boxed = require_circuit(boxed, "boxed")
    if not isinstance(obs_list, Sequence) or isinstance(obs_list, (str, bytes)):
        raise AnswerError("obs_list must be a list of SparsePauliOp observables.")
    if not isinstance(forward_list, Sequence) or isinstance(forward_list, (str, bytes)):
        raise AnswerError("forward_list must be a list with one bounds dictionary per observable.")
    return {
        "ising": _ising_facts(circuit_ising),
        "mirror": _mirror_facts(mirrored),
        "boxes": _box_facts(boxed)["boxes"],
        "obs": [
            {"qubits": int(getattr(obs, "num_qubits", -1)), "terms": sparse_terms(obs, f"obs_list[{i}]")}
            for i, obs in enumerate(obs_list)
        ],
        "forward": [_bound_facts(bounds, f"forward_list[{i}]") for i, bounds in enumerate(forward_list)],
        "backward": _bound_facts(backward, "backward_bound"),
    }


def grade_lab3_ex5(
    circuit_ising: Any,
    mirrored_circuit: Any,
    boxed: Any,
    obs_list: Any,
    forward_list: Any,
    backward_bound: Any,
) -> None:
    """Grade Exercise 5: the 15-qubit Ising mirror, three observables and their light-cone bounds."""
    grade_answer(
        (circuit_ising, mirrored_circuit, boxed, obs_list, forward_list, backward_bound),
        _LAB,
        "ex5",
        reduce=_ex5_answer,
    )
