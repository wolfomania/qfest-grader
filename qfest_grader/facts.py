# This code is part of qfest-grader, licensed under the Apache License,
# Version 2.0 (see LICENSE). Written in 2026 by the Qiskit Fall Fest 2026
# Warsaw organisers; not derived from IBM's qc-grader.

"""Reduce circuits, functions and edge lists to the JSON facts the server compares.

Shared by the Lab 2-4b grading functions. The server receives only these facts,
never a circuit or source code.
"""

from __future__ import annotations

import numbers
from collections.abc import Iterable, Mapping
from typing import Any

from qfest_grader.answers import AnswerError, _as_int

MAX_INSTRUCTIONS = 5000
MAX_EDGES = 5000


def short_error(err: BaseException) -> str:
    """The exception as "Type: message", cut to 200 characters."""
    text = f"{type(err).__name__}: {err}"
    return text[:200]


def call(fn: Any, *args: Any, what: str) -> Any:
    """Call a participant's function; report any exception as an AnswerError."""
    if not callable(fn):
        raise AnswerError(f"{what} must be a function, got {type(fn).__name__}.")
    try:
        return fn(*args)
    except AnswerError:
        raise
    except Exception as err:  # noqa: BLE001 - any failure in participant code is reported
        raise AnswerError(f"{what} raised {short_error(err)}") from None


def require_circuit(value: Any, what: str) -> Any:
    """The value if it is a QuantumCircuit of at most MAX_INSTRUCTIONS instructions."""
    from qiskit import QuantumCircuit

    if not isinstance(value, QuantumCircuit):
        raise AnswerError(f"{what} must return a QuantumCircuit, got {type(value).__name__}.")
    if len(value.data) > MAX_INSTRUCTIONS:
        raise AnswerError(f"{what} has more than {MAX_INSTRUCTIONS} instructions. Simplify it and try again.")
    return value


def count_ops(circuit: Any) -> dict[str, int]:
    """Operation counts as a plain {name: count} dictionary."""
    return {str(name): int(count) for name, count in circuit.count_ops().items()}


def op_sequence(circuit: Any) -> list[str]:
    """Top-level operation names in order, without barriers."""
    return [inst.operation.name for inst in circuit.data if inst.operation.name != "barrier"]


def _indices(circuit: Any, bits: Iterable[Any]) -> list[int]:
    return [circuit.find_bit(bit).index for bit in bits]


def _condition(circuit: Any, operation: Any) -> Any:
    """An if_else condition as [[clbit indices], value], or its text for expressions."""
    condition = getattr(operation, "condition", None)
    if isinstance(condition, tuple) and len(condition) == 2:
        target, value = condition
        bits = target if hasattr(target, "__len__") else [target]  # a register or one clbit
        return [_indices(circuit, bits), int(value)]
    return str(condition)[:200]


def _block_ops(block: Any, outer_qubits: list[int]) -> list[list[Any]]:
    """Operations of a control-flow block as [name, outer qubit indices...], sorted."""
    ops = []
    for inst in block.data:
        if inst.operation.name == "barrier":
            continue
        ops.append([inst.operation.name, *(outer_qubits[block.find_bit(q).index] for q in inst.qubits)])
    return sorted(ops, key=str)


def dynamic_circuit_facts(circuit: Any) -> dict[str, Any]:
    """Structure of a circuit with mid-circuit measurements and if_else feedforward.

    Two circuits share these facts when they have the same operation counts, depth,
    CX pairs, measurements, resets and if_else blocks (condition and body), in any
    order that keeps the depth.
    """
    cx, measures, resets, feedforward = [], [], [], []
    for inst in circuit.data:
        operation = inst.operation
        qubits = _indices(circuit, inst.qubits)
        if operation.name == "cx":
            cx.append(qubits)
        elif operation.name == "measure":
            measures.append([qubits[0], circuit.find_bit(inst.clbits[0]).index])
        elif operation.name == "reset":
            resets.append(qubits[0])
        elif operation.name == "if_else":
            blocks = [_block_ops(block, qubits) for block in operation.blocks if block is not None]
            feedforward.append([_condition(circuit, operation), blocks])
    return {
        "qubits": circuit.num_qubits,
        "clbits": circuit.num_clbits,
        "ops": count_ops(circuit),
        "depth": circuit.depth(),
        "cx": sorted(cx),
        "measures": sorted(measures),
        "resets": sorted(resets),
        "ff": sorted(feedforward, key=str),
    }


def undirected_edges(edges: Any, what: str) -> list[list[int]]:
    """A coupling map, EdgeList or list of pairs as sorted unique [low, high] pairs."""
    if hasattr(edges, "get_edges"):  # CouplingMap
        edges = edges.get_edges()
    if isinstance(edges, (str, bytes, Mapping)) or not isinstance(edges, Iterable):
        raise AnswerError(f"{what} must be a list of qubit pairs, got {type(edges).__name__}.")
    pairs = set()
    for edge in edges:
        if isinstance(edge, (str, bytes)) or not isinstance(edge, Iterable):
            raise AnswerError(f"{what} must contain qubit pairs such as (0, 1), got {edge!r}.")
        edge = list(edge)
        if len(edge) != 2:
            raise AnswerError(f"{what} must contain qubit pairs such as (0, 1), got {edge!r}.")
        a, b = (_as_int(q, f"A qubit index in {what}") for q in edge)
        pairs.add((min(a, b), max(a, b)))
        if len(pairs) > MAX_EDGES:
            raise AnswerError(f"{what} has more than {MAX_EDGES} edges.")
    return [list(pair) for pair in sorted(pairs)]


def string_list(values: Any, what: str) -> list[str]:
    """A list, tuple or set of strings as a sorted list without duplicates."""
    if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, Iterable):
        raise AnswerError(f"{what} must be a list of strings, got {type(values).__name__}.")
    items = list(values)
    if not all(isinstance(item, str) for item in items):
        raise AnswerError(f"{what} must contain only strings.")
    return sorted(set(items))


def int_list(values: Any, what: str) -> list[int]:
    """A sequence of whole numbers, order kept."""
    if isinstance(values, (str, bytes, Mapping)) or not isinstance(values, Iterable):
        raise AnswerError(f"{what} must be a list of whole numbers, got {type(values).__name__}.")
    return [_as_int(value, f"An entry of {what}") for value in values]


def plain_number(value: Any, what: str) -> int | float:
    """A whole number as int, another real number as float."""
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise AnswerError(f"{what} must be a number, got {value!r}.")
    if float(value).is_integer():
        return int(value)
    return float(value)
