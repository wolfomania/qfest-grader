import itertools
import math
import sys
from types import SimpleNamespace

import networkx as nx
import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.quantum_info import SparsePauliOp

from qfest_grader.answers import AnswerError
from qfest_grader.challenges.warsaw_2026 import lab4a
from qfest_grader.facts import unroll_boxes


def complete_graph(numbers, weight="weight"):
    graph = nx.Graph()
    graph.add_nodes_from(range(len(numbers)))
    for i, j in itertools.combinations(range(len(numbers)), 2):
        graph.add_edge(i, j, **{weight: numbers[i] + numbers[j]})
    return graph


def test_graph_facts_sort_edges_and_read_weights():
    facts = lab4a._graph_facts(complete_graph([3, 5, 7]), "g")
    assert facts == {"nodes": [0, 1, 2], "num_edges": 3, "edges": [[0, 1, 8], [0, 2, 10], [1, 2, 12]]}
    unweighted = lab4a._graph_facts(complete_graph([3, 5], weight="w"), "g")
    assert unweighted["edges"] == [[0, 1, None]]
    with pytest.raises(AnswerError, match="networkx Graph"):
        lab4a._graph_facts([1, 2], "g")


def test_unroll_boxes_keeps_the_operations_in_order():
    qc = QuantumCircuit(2)
    with qc.box():
        qc.h(0)
        qc.cx(0, 1)
    qc.rz(0.5, 1)
    flat = unroll_boxes(qc)
    assert [inst.operation.name for inst in flat.data] == ["h", "cx", "rz"]
    assert [flat.find_bit(q).index for q in flat.data[1].qubits] == [0, 1]
    plain = QuantumCircuit(1)
    assert unroll_boxes(plain) is plain


def test_bound_circuit_assigns_fixed_values_in_parameter_order():
    beta, gamma = Parameter("β"), Parameter("γ")
    qc = QuantumCircuit(1)
    qc.rx(gamma, 0)
    qc.rz(beta, 0)
    unrolled, bound = lab4a._bound_circuit(qc, "circuit")
    assert unrolled.num_parameters == 2 and bound.num_parameters == 0
    assert [float(inst.operation.params[0]) for inst in bound.data] == [0.61, 0.37]


def test_ex1b_sends_hamiltonian_terms_and_state():
    hamiltonian = SparsePauliOp.from_sparse_list([("ZZ", [0, 1], 7.5)], num_qubits=2)
    gamma = Parameter("γ")
    qc = QuantumCircuit(2)
    qc.h([0, 1])
    qc.rzz(gamma, 0, 1)
    facts = lab4a._ex1b_answer((hamiltonian, qc))
    assert facts["hamiltonian"]["terms"] == [["ZZ", [0, 1], 7.5, 0.0]]
    assert facts["num_parameters"] == 1 and facts["state"]["num_qubits"] == 2 and len(facts["state"]["amps"]) == 4


def test_sampler_and_estimator_facts_read_the_option_paths():
    runtime = pytest.importorskip("qiskit_ibm_runtime")
    sampler = runtime.options.SamplerOptions()
    sampler.default_shots = 123
    sampler.dynamical_decoupling.enable = False
    sampler.dynamical_decoupling.sequence_type = "XY4"
    facts = lab4a._sampler_facts(sampler, "options")
    assert facts["default_shots"] == 123 and facts["dd_enable"] is False and facts["dd_sequence"] == "XY4"
    assert facts["twirl_gates"] is None
    estimator = runtime.options.EstimatorOptions()
    estimator.resilience.measure_mitigation = False
    assert lab4a._estimator_facts(estimator, "est")["measure_mitigation"] is False


def test_measurement_map_and_m3_facts():
    qc = QuantumCircuit(3, 2)
    qc.measure(2, 0)
    qc.measure(1, 1)
    options = SimpleNamespace(default_shots=1000, dynamical_decoupling=SimpleNamespace(enable=None, sequence_type=None),
                              twirling=SimpleNamespace(enable_gates=None, enable_measure=None, num_randomizations=None))
    facts = lab4a._m3_answer((options, qc, {0: 2, 1: 1}, {"01": 0.6, "10": 0.4}, {"01": 6, "10": 4}), "v3")
    assert facts["meas_map_matches"] is True
    assert facts["quasis"] == {"keys": 2, "key_bits": [2], "total": 1.0} and facts["counts"]["total"] == 10
    assert lab4a._m3_answer((options, qc, [1, 2], {}, {}), "v3")["meas_map_matches"] is False


def test_most_likely_difference_follows_analyze_partition_result():
    assert lab4a._most_likely_difference({"000111": 0.7, "000000": 0.3}, "p") == 18
    assert lab4a._most_likely_difference({"000000": 1.0}, "p") == 48
    assert lab4a._most_likely_difference({}, "p") is None
    with pytest.raises(AnswerError, match="6-bit string keys"):
        lab4a._most_likely_difference({"0011": 1.0}, "p")


def test_ex3a_calls_the_function_for_every_size():
    facts = lab4a._ex3a_answer((lambda n: math.ceil(n ** 0.5), range(2), [2], (3,)))
    assert facts["final_qubits"] == [5, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    assert facts["node_x"] == [0, 1] and facts["node_z"] == [3]
    with pytest.raises(AnswerError, match="whole number"):
        lab4a._ex3a_answer((lambda n: n / 7, [], [], []))


def two_body(paulis, pairs):
    return [SparsePauliOp.from_sparse_list([(paulis, list(pair), 1.0)], num_qubits=3) for pair in pairs]


def test_ex3c_compares_the_circuit_with_the_ansatz_of_the_submitted_hamiltonian():
    qopt = pytest.importorskip("qopt_best_practices.circuit_library")
    terms = two_body("XX", [(0, 1)]) + two_body("YY", [(0, 2)]) + two_body("ZZ", [(1, 2)])
    forward, backward = SparsePauliOp.sum(terms), SparsePauliOp.sum(terms[::-1])
    facts = lab4a._ex3c_answer((backward, qopt.annotated_qaoa_ansatz(backward, reps=2)))
    assert facts["own_ansatz"] is True and facts["num_parameters"] == 4
    assert lab4a._ex3c_answer((forward, qopt.annotated_qaoa_ansatz(backward, reps=2)))["own_ansatz"] is False
    assert lab4a._ex3c_answer((forward, QuantumCircuit(4)))["own_ansatz"] is None


def test_ex3c_needs_qopt_best_practices(monkeypatch):
    monkeypatch.setitem(sys.modules, "qopt_best_practices.circuit_library", None)
    with pytest.raises(AnswerError, match="qopt_best_practices"):
        lab4a._ex3c_answer((SparsePauliOp.sum(two_body("ZZ", [(0, 1)])), QuantumCircuit(3)))


def estimator_job(values):
    pubs = [SimpleNamespace(data=SimpleNamespace(evs=np.array(chunk))) for chunk in values]
    return SimpleNamespace(result=lambda: pubs)


def test_exp_map_matches_compares_with_the_job_result():
    job = estimator_job([[0.5, -0.25], [0.125]])
    assert lab4a._job_exp_map(job, "job") == {0: 0.5, 1: -0.25, 2: 0.125}
    assert lab4a._exp_map_matches({0: np.float64(0.5), 1: -0.25, 2: 0.125}, job, "job")
    assert not lab4a._exp_map_matches({0: 0.5, 1: -0.25}, job, "job")
    assert not lab4a._exp_map_matches(None, job, "job")


def test_ex4_recomputes_the_differences_and_finds_the_best_method():
    job = estimator_job([[0.1, -0.2]])
    results = {name: {"set0": [5, 3], "set1": [4 + i], "exp_map": {0: 0.1, 1: -0.2}}
               for i, name in enumerate(lab4a._METHODS)}
    facts = lab4a._ex4_answer(([], results, [job] * 4))
    assert facts["best_method"] == "PEC" and facts["best_difference"] == 1
    assert facts["methods"]["No EM"]["numbers"] == lab4a._numbers_digest([3, 4, 5])
    with pytest.raises(AnswerError, match="exactly the keys"):
        lab4a._ex4_answer(([], {"No EM": {}}, [job]))


def test_exbonus_rebuilds_the_sets_from_the_bits():
    job = estimator_job([[0.3]])
    result = {"set0": [4], "set1": [6, 1], "exp_map": {0: 0.3}}
    facts = lab4a._exbonus_answer((result, [0, 1, 0], np.array([6, 4, 1]), job))
    assert facts["bits_match"] and facts["bits_valid"] and facts["exp_map_matches"]
    assert lab4a._exbonus_answer((result, np.array([False, True, False]), [6, 4, 1], job)) == facts
    assert facts["difference"] == 3 and facts["count"] == 3 and facts["hardware_job"] is False
    with pytest.raises(AnswerError, match="one bit per number"):
        lab4a._exbonus_answer((result, [0, 1], [6, 4, 1], job))
