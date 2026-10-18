import pytest
from qiskit import QuantumCircuit

from qfest_grader import check_progress, save_account
from qfest_grader.api import GraderError
from qfest_grader.challenges.warsaw_2026 import (
    grade_lab0_ex1,
    grade_lab0_ex2,
    grade_lab0_ex3,
    grade_lab1_ex2,
    grade_lab1_ex7,
)
from qfest_grader.challenges.warsaw_2026.lab0 import grade_lab0_ex4
from qfest_grader.grade import determine_grade_response, determine_progress_response


@pytest.fixture
def account(rpc_calls):
    save_account("student@uni.pl", verify=False)
    return rpc_calls


def test_grade_sends_email_lab_exercise_and_reduced_answer(account, capsys):
    account.reply = {"passed": True, "score": 1.0, "msg": "🎉 Correct!"}
    grade_lab0_ex2({"0": 6, "1": 4})

    function, body = account.calls[0]
    assert function == "qf_submit"
    assert body["p_email"] == "student@uni.pl"
    assert (body["p_lab"], body["p_exercise"]) == ("lab0", "ex2")
    assert body["p_answer"] == {"0": 6, "1": 4}
    assert body["p_client"].startswith("qfest-grader/")
    out = capsys.readouterr().out
    assert "🎉 Correct!" in out and "You scored 1.0 on this exercise." in out


def test_grade_lab0_ex1_sends_hello(account):
    grade_lab0_ex1()
    assert account.calls[0][1]["p_answer"] == "hello"


def test_grade_reports_failure(account, capsys):
    account.reply = {"passed": False, "score": 0, "msg": "Too far from 50/50."}
    grade_lab0_ex3(0.5)
    out = capsys.readouterr().out
    assert "Not quite! Too far from 50/50." in out
    assert "Please review your answer" in out


def test_invalid_answer_is_reported_without_network(account, capsys):
    grade_lab0_ex3([0.1, 0.2])
    assert account.calls == []
    assert "Not quite! Submit a single number" in capsys.readouterr().out


def test_missing_account_explains_setup(rpc_calls, capsys):
    grade_lab0_ex1()
    assert rpc_calls.calls == []
    assert "Failed: No grader account found" in capsys.readouterr().out


def test_server_error_is_printed(account, capsys):
    account.reply = GraderError("The grading server returned 500: boom")
    grade_lab0_ex1()
    assert "Failed: The grading server returned 500: boom" in capsys.readouterr().out


def test_unexpected_server_reply_suggests_update(account, capsys):
    account.reply = {"something": "else"}
    grade_lab0_ex1()
    assert "unexpected response" in capsys.readouterr().out


def test_statevector_and_dict_answers_are_reduced(account):
    qc = QuantumCircuit(1)
    qc.h(0)
    grade_lab0_ex4(qc)
    grade_lab1_ex2({"a": 2, "b": 5})
    assert account.calls[0][1]["p_answer"]["num_qubits"] == 1
    assert account.calls[1][1]["p_answer"] == {"a": 2, "b": 5}


def test_stabilizer_answer_is_sent_for_large_circuits(account):
    qc = QuantumCircuit(30)
    qc.h(0)
    for q in range(29):
        qc.cx(q, q + 1)
    grade_lab1_ex7(qc)
    answer = account.calls[0][1]["p_answer"]
    assert answer["xall"] == 1 and len(answer["zz"]) == 29


def test_determine_grade_response_partial_score():
    text = determine_grade_response(passed=False, score=1, msg="One of two.")
    assert "Not quite! One of two." in text and "You scored 1" in text


PROGRESS = {
    "challenge_aggregate": {"score_total": 1.0, "num_exercises_passed": 1, "num_exercises": 2},
    "per_lab": [
        {
            "name": "lab0",
            "score_total": 1.0,
            "num_exercises_passed": 1,
            "num_exercises": 2,
            "per_exercise": [
                {"name": "ex1", "score": 1.0, "passed": True},
                {"name": "ex2", "score": 0.0, "passed": False},
            ],
        }
    ],
}


def test_check_progress_prints_lab_summary(account, capsys):
    account.reply = PROGRESS
    check_progress("lab0")
    assert account.calls[0] == ("qf_progress", {"p_email": "student@uni.pl", "p_lab": "lab0"})
    out = capsys.readouterr().out
    assert 'Lab "lab0" — 1/2 passed, score 1.0' in out
    assert "✅ ex1" in out and "⬜ ex2" in out


def test_check_progress_all_labs(account, capsys):
    account.reply = PROGRESS
    check_progress()
    assert "Exercises passed: 1/2" in capsys.readouterr().out


def test_progress_for_unknown_lab():
    assert "No lab named" in determine_progress_response({"per_lab": []}, lab_name="lab9")
