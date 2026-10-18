# This code is part of qfest-grader, licensed under the Apache License,
# Version 2.0 (see LICENSE). Written in 2026 by the Qiskit Fall Fest 2026
# Warsaw organisers; not derived from IBM's qc-grader.

"""Reduce Pauli operators (SparsePauliOp, PauliLindbladMap) to canonical JSON terms."""

from __future__ import annotations

from typing import Any

from qfest_grader.answers import AnswerError
from qfest_grader.facts import short_error

MAX_TERMS_SENT = 200
MAX_TERMS = 1_000_000


def sparse_terms(op: Any, what: str) -> list[list[Any]]:
    """Terms as [paulis, qubits, re, im], identity factors dropped, qubits ascending, terms sorted.

    Works for any object with to_sparse_list(), such as SparsePauliOp.
    """
    try:
        items = op.to_sparse_list()
    except Exception as err:  # noqa: BLE001
        raise AnswerError(f"{what} must be a SparsePauliOp, got {type(op).__name__} ({short_error(err)}).") from None
    if len(items) > MAX_TERMS:
        raise AnswerError(f"{what} has more than {MAX_TERMS} terms.")
    terms = []
    for paulis, qubits, coeff in items:
        pairs = sorted((int(q), p) for p, q in zip(paulis, qubits) if p != "I")
        c = complex(coeff)
        terms.append(["".join(p for _, p in pairs), [q for q, _ in pairs], round(c.real, 12), round(c.imag, 12)])
    return sorted(terms, key=lambda t: (t[1], t[0], t[2], t[3]))


def observable_facts(op: Any, what: str, top: int | None = None) -> dict[str, Any]:
    """Qubit count, term count and either every term or the `top` largest terms by |coefficient|.

    The top terms come as top_paulis ([paulis, qubits], canonical order) and top_coeffs (real parts,
    same order).
    """
    terms = sparse_terms(op, what)
    facts: dict[str, Any] = {
        "qubits": int(getattr(op, "num_qubits", -1)),
        "num_terms": len(terms),
        "imag_max": max((abs(t[3]) for t in terms), default=0.0),
    }
    if top is None:
        if len(terms) > MAX_TERMS_SENT:
            raise AnswerError(f"{what} has {len(terms)} terms, far more than expected.")
        facts["terms"] = terms
    else:
        best = sorted(sorted(terms, key=lambda t: -abs(complex(t[2], t[3])))[:top], key=lambda t: (t[1], t[0]))
        facts["top_paulis"] = [[t[0], t[1]] for t in best]
        facts["top_coeffs"] = [t[2] for t in best]
    return facts
