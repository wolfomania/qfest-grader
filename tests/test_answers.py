import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from qfest_grader import answers
from qfest_grader.answers import (
    AnswerError,
    circuit_facts,
    circuit_state_answer,
    counts_answer,
    ghz_stabilizer_answer,
    int_dict_answer,
    scalar_answer,
    sparse_amplitudes,
    statevector_answer,
)


def test_counts_answer_converts_numpy_integers():
    assert counts_answer({"0": np.int64(5), 1: 7.0}) == {"0": 5, "1": 7}


@pytest.mark.parametrize("bad", [[1, 2], {"0": 1.5}, {"0": True}, {"0": "3"}, None])
def test_counts_answer_rejects_bad_input(bad):
    with pytest.raises(AnswerError):
        counts_answer(bad)


@pytest.mark.parametrize("value", [0.25, np.float64(0.25), np.array(0.25), np.array([0.25]), 0.25 + 0j])
def test_scalar_answer_accepts_single_numbers(value):
    assert scalar_answer(value) == 0.25


@pytest.mark.parametrize("bad", [np.array([0.1, 0.2]), float("nan"), float("inf"), 1 + 1j, "x", None])
def test_scalar_answer_rejects_non_scalars(bad):
    with pytest.raises(AnswerError):
        scalar_answer(bad)


def test_int_dict_answer_requires_all_keys():
    assert int_dict_answer({"a": 2, "b": np.int32(4), "extra": 9}, ("a", "b")) == {"a": 2, "b": 4}
    with pytest.raises(AnswerError, match="'b'"):
        int_dict_answer({"a": 2}, ("a", "b"))
    with pytest.raises(AnswerError):
        int_dict_answer([2, 4], ("a", "b"))
    with pytest.raises(AnswerError):
        int_dict_answer({"a": None, "b": 1}, ("a", "b"))


def test_sparse_amplitudes_normalises_and_drops_zeros():
    n, amps = sparse_amplitudes([3, 0, 0, 4j])
    assert n == 2
    assert amps == [[0, 0.6, 0.0], [3, 0.0, 0.8]]


def test_sparse_amplitudes_keeps_largest_when_truncating(monkeypatch):
    monkeypatch.setattr(answers, "MAX_AMPLITUDES", 2)
    _, amps = sparse_amplitudes([0.1, 0.9, 0.2, 0.3])
    assert [a[0] for a in amps] == [1, 3]


@pytest.mark.parametrize("bad", [[1, 0, 0], [], [0, 0], [np.nan, 1]])
def test_sparse_amplitudes_rejects_invalid_vectors(bad):
    with pytest.raises(AnswerError):
        sparse_amplitudes(bad)


def test_statevector_answer_from_statevector():
    qc = QuantumCircuit(2)
    qc.h(1)
    result = statevector_answer(Statevector(qc))
    assert result["num_qubits"] == 2
    assert [a[0] for a in result["amps"]] == [0, 2]


def test_statevector_answer_accepts_circuit():
    qc = QuantumCircuit(1)
    qc.x(0)
    assert statevector_answer(qc)["amps"] == [[1, 1.0, 0.0]]


def test_circuit_facts_lists_multi_qubit_gates_and_skips_barriers():
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.barrier()
    qc.cx(0, 2)
    qc.cz(2, 1)
    qc.ccx(0, 1, 2)
    facts = circuit_facts(qc)
    assert facts["multi"] == [[0, 2], [2, 1], [0, 1, 2]]
    assert facts["num_qubits"] == 3
    assert facts["depth"] == qc.depth()


def test_circuit_state_answer_ignores_final_measurements():
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    with_meas = qc.copy()
    with_meas.measure_all()
    assert circuit_state_answer(with_meas) == circuit_state_answer(qc)
    assert circuit_state_answer(with_meas)["depth"] == 2


def test_circuit_state_answer_reports_mid_circuit_measurement():
    qc = QuantumCircuit(2, 1)
    qc.h(0)
    qc.measure(0, 0)
    qc.cx(0, 1)
    result = circuit_state_answer(qc)
    assert "error" in result and "amps" not in result


def test_circuit_state_answer_refuses_large_statevectors(monkeypatch):
    monkeypatch.setattr(answers, "MAX_STATEVECTOR_QUBITS", 3)
    result = circuit_state_answer(QuantumCircuit(4))
    assert "too many" in result["error"]


def test_circuit_state_answer_requires_a_circuit():
    with pytest.raises(AnswerError, match="QuantumCircuit"):
        circuit_state_answer("not a circuit")


def _chain_ghz(n, root_gate="h"):
    qc = QuantumCircuit(n)
    getattr(qc, root_gate)(0)
    for q in range(n - 1):
        qc.cx(q, q + 1)
    qc.measure_all()
    return qc


def test_ghz_stabilizer_answer_identifies_ghz():
    result = ghz_stabilizer_answer(_chain_ghz(12))
    assert result["xall"] == 1
    assert result["zz"] == [1] * 11
    assert result["num_qubits"] == 12
    assert len(result["multi"]) == 11


def test_ghz_stabilizer_answer_detects_product_state():
    qc = QuantumCircuit(4)
    qc.h(0)
    result = ghz_stabilizer_answer(qc)
    assert result["zz"][0] == 0 and result["zz"][1:] == [1, 1]
    assert result["xall"] == 0


def test_ghz_stabilizer_answer_detects_relative_sign():
    qc = QuantumCircuit(3)
    qc.x(0)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    result = ghz_stabilizer_answer(qc)
    assert result["xall"] == -1 and result["zz"] == [1, 1]


def test_ghz_stabilizer_answer_reports_non_clifford_gates():
    qc = QuantumCircuit(2)
    qc.t(0)
    assert "error" in ghz_stabilizer_answer(qc)


def test_circuit_facts_expands_custom_gates():
    inner = QuantumCircuit(3)
    inner.h(0)
    inner.cx(0, 1)
    inner.cx(1, 2)
    qc = QuantumCircuit(3)
    qc.append(inner.to_gate(), [0, 1, 2])
    facts = circuit_facts(qc)
    assert facts["multi"] == [[0, 1], [1, 2]]
    assert facts["depth"] == 3


def test_circuit_state_answer_counts_the_real_depth_of_state_preparation():
    qc = QuantumCircuit(2)
    qc.initialize([0, 2**-0.5, 2**-0.5, 0], [0, 1])
    answer = circuit_state_answer(qc)
    assert answer["depth"] > 1
    assert answer["amps"] == [[1, pytest.approx(2**-0.5), 0.0], [2, pytest.approx(2**-0.5), 0.0]]


def test_circuit_facts_rejects_gates_without_definition():
    from qiskit.circuit import Gate

    qc = QuantumCircuit(2)
    qc.append(Gate("mystery", 2, []), [0, 1])
    with pytest.raises(AnswerError, match="mystery"):
        circuit_facts(qc)


def test_circuit_facts_rejects_too_many_multi_qubit_gates(monkeypatch):
    monkeypatch.setattr(answers, "MAX_GATES", 3)
    qc = QuantumCircuit(2)
    for _ in range(4):
        qc.cx(0, 1)
    with pytest.raises(AnswerError, match="more than 3"):
        circuit_facts(qc)
