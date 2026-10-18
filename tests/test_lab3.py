import math
from types import SimpleNamespace

import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp

from qfest_grader.answers import AnswerError
from qfest_grader.challenges.warsaw_2026 import lab3
from qfest_grader.options import option_value, plain
from qfest_grader.paulis import observable_facts, sparse_terms


def test_plain_turns_unset_none_tuples_and_floats_into_json():
    unset_type = type("UnsetType", (), {})
    assert plain(unset_type()) is None
    assert plain((1.0, 3, 5.5)) == [1, 3, 5.5]
    assert plain(True) is True
    assert plain("XY4") == "XY4"


def test_option_value_follows_dotted_paths_and_reports_missing_ones():
    opts = SimpleNamespace(resilience=SimpleNamespace(zne=SimpleNamespace(noise_factors=(1, 2))))
    assert option_value(opts, "resilience.zne.noise_factors", "zne") == [1, 2]
    with pytest.raises(AnswerError, match="zne.amplifier is missing"):
        option_value(opts, "resilience.zne.amplifier", "zne.amplifier")


def test_ex1_reads_every_method_from_estimator_options():
    runtime = pytest.importorskip("qiskit_ibm_runtime")
    options = {key: runtime.options.EstimatorOptions() for key in ("dd", "pt", "trex", "zne", "pec")}
    options["dd"].dynamical_decoupling.enable = True
    options["dd"].dynamical_decoupling.sequence_type = "XX"
    options["zne"].resilience.zne.noise_factors = (1, 2, 3)
    facts = lab3._ex1_answer(options)
    assert facts["dd"] == {"enable": True, "sequence_type": "XX"}
    assert facts["zne"]["noise_factors"] == [1, 2, 3]
    assert facts["pt"]["num_randomizations"] is None or isinstance(facts["pt"]["num_randomizations"], (int, str))
    with pytest.raises(AnswerError, match="exactly the keys"):
        lab3._ex1_answer({"dd": options["dd"]})


def test_sparse_terms_are_canonical():
    op = SparsePauliOp.from_sparse_list([("XZ", [11, 3], 2.0), ("Z", [0], 1j), ("", [], 0.5)], num_qubits=12)
    assert sparse_terms(op, "op") == [["", [], 0.5, 0.0], ["Z", [0], 0.0, 1.0], ["ZX", [3, 11], 2.0, 0.0]]
    with pytest.raises(AnswerError, match="must be a SparsePauliOp"):
        sparse_terms("Z", "op")


def test_observable_facts_send_all_terms_or_only_the_largest():
    op = SparsePauliOp.from_sparse_list([("Z", [q], 1.0 + q / 10) for q in range(5)] + [("XX", [0, 1], 0.01)], num_qubits=5)
    facts = observable_facts(op, "op")
    assert facts["qubits"] == 5 and facts["num_terms"] == 6 and len(facts["terms"]) == 6
    top = observable_facts(op, "op", top=2)
    assert top["top_paulis"] == [["Z", [3]], ["Z", [4]]] and top["top_coeffs"] == [1.3, 1.4]
    assert "terms" not in top


def test_circuit_facts_of_ising_and_mirror():
    qc = QuantumCircuit(2)
    qc.rx(math.pi / 8, [0, 1])
    qc.barrier()
    qc.cz(0, 1)
    ising = lab3._ising_facts(qc)
    assert ising == {"qubits": 2, "ops": {"rx": 2, "cz": 1}, "barriers": 1, "rx_all_pi8": True}
    mirror = qc.compose(qc.inverse())
    mirror.measure_all()
    facts = lab3._mirror_facts(mirror)
    assert facts["measures"] == 2 and facts["zero_fidelity"] == pytest.approx(1.0)
    assert "barrier" not in facts["ops"]


def test_box_facts_count_annotated_gate_boxes():
    pytest.importorskip("samplomatic")
    from samplomatic.transpiler import generate_boxing_pass_manager

    qc = QuantumCircuit(2)
    qc.sx(0)
    qc.cz(0, 1)
    qc.measure_all()
    boxed = generate_boxing_pass_manager(
        enable_gates=True, enable_measures=True, twirling_strategy="active",
        inject_noise_targets="gates", inject_noise_strategy="no_modification",
    ).run(qc)
    facts = lab3._box_facts(boxed)
    assert facts["boxes"] >= 2 and facts["gate_boxes"] >= 1
    assert facts["gate_boxes_twirl"] == facts["gate_boxes"] == facts["gate_boxes_inject"]


def _program(circuit, samplex):
    return SimpleNamespace(items=[SimpleNamespace(circuit=circuit, samplex=samplex)])


def test_ex3_facts_compare_noise_slots_and_program_items():
    template = QuantumCircuit(1)
    specs = [SimpleNamespace(name="pauli_lindblad_maps.r1"), SimpleNamespace(name="noise_scales.r1")]
    samplex = SimpleNamespace(inputs=lambda: SimpleNamespace(get_specs=lambda: specs))
    args = SimpleNamespace(fully_bound=True)
    facts = lab3._ex3_answer((template, samplex, args, _program(template, samplex), {"r1": object()}))
    assert facts["slots_match_noise"] and facts["item_circuit_matches"] and facts["item_samplex_matches"]
    other = lab3._ex3_answer((template, samplex, args, _program(QuantumCircuit(1), None), {"r2": object()}))
    assert not other["slots_match_noise"] and not other["item_circuit_matches"]
    with pytest.raises(AnswerError, match="not a samplex"):
        lab3._ex3_answer((template, object(), args, _program(template, samplex), {}))


def test_bound_facts_flag_negative_or_infinite_rates():
    from qiskit.quantum_info import PauliLindbladMap

    good = {"a": PauliLindbladMap.from_sparse_list([("X", [0], 0.1), ("ZZ", [0, 1], 0.0)], num_qubits=2)}
    assert lab3._bound_facts(good, "b") == {"keys": 1, "terms": 2, "finite_nonneg": True}
    bad = {"a": PauliLindbladMap.from_sparse_list([("X", [0], -0.1)], num_qubits=1)}
    assert lab3._bound_facts(bad, "b")["finite_nonneg"] is False
    with pytest.raises(AnswerError, match="dictionary"):
        lab3._bound_facts([1], "b")
