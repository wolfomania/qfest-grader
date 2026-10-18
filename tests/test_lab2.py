import numpy as np
import pytest
import rustworkx as rx
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.transpiler import CouplingMap

from qfest_grader import save_account
from qfest_grader.answers import AnswerError
from qfest_grader.challenges.warsaw_2026 import (
    grade_lab2_ex1,
    grade_lab2_ex2,
    grade_lab2_ex4,
    grade_lab2_ex5,
    grade_lab2_ex6,
    grade_lab2_ex7,
)
from qfest_grader.challenges.warsaw_2026.lab2 import (
    _ex4_answer,
    _params_answer,
    _repeated_circuits,
)
from qfest_grader.facts import dynamic_circuit_facts, string_list, undirected_edges


@pytest.fixture
def account(rpc_calls):
    save_account("student@uni.pl", verify=False)
    return rpc_calls


def sent(account):
    return account.calls[-1][1]["p_answer"]


def test_edges_from_coupling_map_edge_list_and_pairs_are_undirected_and_unique():
    expected = [[0, 1], [1, 2]]
    assert undirected_edges(CouplingMap([[0, 1], [1, 0], [2, 1]]), "cm") == expected
    graph = rx.PyDiGraph()
    graph.add_nodes_from(range(3))
    graph.add_edges_from_no_data([(1, 0), (1, 2)])
    assert undirected_edges(graph.edge_list(), "cm") == expected
    assert undirected_edges([(1, 0), [1, 2], (np.int64(2), np.int64(1))], "cm") == expected


@pytest.mark.parametrize("bad", ["01", [(0, 1, 2)], [(0, "a")], 5, {"a": 1}])
def test_bad_edges_are_refused(bad):
    with pytest.raises(AnswerError):
        undirected_edges(bad, "coupling_map")


def test_string_list_sorts_and_deduplicates():
    assert string_list(["x", "cz", "x"], "ops") == ["cz", "x"]
    with pytest.raises(AnswerError):
        string_list(["x", 1], "ops")
    with pytest.raises(AnswerError):
        string_list("cz", "ops")


def test_ex1_sends_sorted_operations_and_edges(account):
    grade_lab2_ex1({"x", "cz"}, CouplingMap([[1, 0], [0, 1]]).get_edges())
    assert sent(account) == {"ops": ["cz", "x"], "edges": [[0, 1]]}


def _x_then_measure(n):
    qc = QuantumCircuit(1, 1)
    for _ in range(n):
        qc.x(0)
        qc.barrier()
    qc.measure(0, 0)
    return qc


def test_repeated_circuits_send_operation_sequences_without_barriers():
    facts = _repeated_circuits(_x_then_measure, "f")
    assert set(facts) == {"0", "1", "2", "3", "5", "10"}
    assert facts["2"] == {"qubits": 1, "seq": ["x", "x", "measure"]}


def test_repeated_circuits_report_participant_errors():
    def broken(n):
        raise ValueError("boom")

    with pytest.raises(AnswerError, match=r"f\(0\) raised ValueError: boom"):
        _repeated_circuits(broken, "f")
    with pytest.raises(AnswerError, match="must return a QuantumCircuit"):
        _repeated_circuits(lambda n: None, "f")
    with pytest.raises(AnswerError, match="too large"):
        _repeated_circuits(lambda n: QuantumCircuit(21), "f")


def test_grade_ex2_prints_error_without_submitting(account, capsys):
    grade_lab2_ex2(lambda n: "not a circuit")
    assert account.calls == []
    assert "must return a QuantumCircuit" in capsys.readouterr().out


def _visibility(value):
    return {e: {"bit-flip sensitive": value, "phase-flip sensitive": value} for e in ("X error", "Y error", "Z error")}


def test_ex4_requires_every_key_and_booleans():
    assert _ex4_answer(_visibility(True))["Y error"] == {"bit-flip sensitive": True, "phase-flip sensitive": True}
    with pytest.raises(AnswerError, match="replace None"):
        _ex4_answer(_visibility(None))
    with pytest.raises(AnswerError, match="True or False"):
        _ex4_answer(_visibility(1))
    with pytest.raises(AnswerError, match="exactly the keys"):
        _ex4_answer({"X error": {}})


def test_grade_ex4_sends_the_dictionary(account):
    grade_lab2_ex4(_visibility(False))
    assert sent(account)["Z error"] == {"bit-flip sensitive": False, "phase-flip sensitive": False}


def test_ex5_sends_layout_basis_and_swap_counts_on_five_circuits(account):
    def count_swaps(circuit):
        return sum(1 for inst in circuit.data if inst.operation.name == "swap")

    grade_lab2_ex5(range(3), ["swap", "h", "cx", "h"], count_swaps)
    answer = sent(account)
    assert answer["layout"] == [0, 1, 2]
    assert answer["basis"] == ["cx", "h", "swap"]
    assert len(answer["swaps"]) == 5 and all(isinstance(c, int) for c in answer["swaps"])


def _feedforward_circuit(n):
    qr, cr = QuantumRegister(n, "q"), ClassicalRegister(n, "c")
    qc = QuantumCircuit(qr, cr)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(1, 0)
    qc.reset(1)
    with qc.if_test((cr[0], 1)):
        qc.x(n - 1)
        qc.x(2)
    qc.measure(qr, cr)
    return qc


def test_dynamic_circuit_facts_capture_structure():
    facts = dynamic_circuit_facts(_feedforward_circuit(4))
    assert facts["qubits"] == 4 and facts["clbits"] == 4
    assert facts["ops"] == {"measure": 5, "h": 1, "cx": 1, "reset": 1, "if_else": 1}
    assert facts["cx"] == [[0, 1]]
    assert facts["resets"] == [1]
    assert facts["measures"] == [[0, 0], [1, 0], [1, 1], [2, 2], [3, 3]]
    assert facts["ff"] == [[[[0], 1], [[["x", 2], ["x", 3]]]]]
    assert facts["depth"] == _feedforward_circuit(4).depth()


def test_grade_ex6_sends_facts_for_six_sizes(account):
    grade_lab2_ex6(build_circuit=_feedforward_circuit)
    assert set(sent(account)) == {"4", "6", "8", "10", "12", "20"}


def _params(circuit):
    return {
        "Number of qubits": np.int64(circuit.num_qubits),
        "Depth": circuit.depth(),
        "2-qubit depth": 2.0,
        "Gates": circuit.count_ops(),
        "Multi-qubit gates": circuit.num_nonlocal_gates(),
        "Number of ancillas": 0,
    }


def test_params_are_normalised_to_plain_numbers():
    params = _params_answer(_params(_feedforward_circuit(4)))
    assert params["Number of qubits"] == 4 and type(params["Number of qubits"]) is int
    assert params["2-qubit depth"] == 2 and type(params["2-qubit depth"]) is int
    assert params["Gates"]["measure"] == 5
    with pytest.raises(AnswerError, match="'Depth'"):
        _params_answer({k: v for k, v in _params(_feedforward_circuit(4)).items() if k != "Depth"})
    with pytest.raises(AnswerError, match="must be a number"):
        _params_answer({**_params(_feedforward_circuit(4)), "Depth": "nine"})


def test_grade_ex7_sends_build_facts_and_params(account):
    grade_lab2_ex7(quantum_circuit_params=_params, build_circuit=_feedforward_circuit)
    answer = sent(account)
    assert set(answer) == {"4", "6", "8"}
    assert answer["6"]["build"] == dynamic_circuit_facts(_feedforward_circuit(6))
    assert answer["6"]["params"]["Gates"]["if_else"] == 1
