# This code is part of qfest-grader, licensed under the Apache License,
# Version 2.0 (see LICENSE). Written in 2026 by the Qiskit Fall Fest 2026
# Warsaw organisers; not derived from IBM's qc-grader.

"""Read Qiskit Runtime options objects as plain JSON values."""

from __future__ import annotations

import numbers
from typing import Any

from qfest_grader.answers import AnswerError

_MISSING = object()


def plain(value: Any) -> Any:
    """An options value as JSON: unset values become None, sequences become lists."""
    if value is None or type(value).__name__ == "UnsetType":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        number = float(value)
        return int(number) if number.is_integer() else number
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    return str(value)[:100]


def option_value(options: Any, path: str, what: str) -> Any:
    """The value at a dotted attribute path such as 'resilience.zne.amplifier', as JSON."""
    value = options
    for name in path.split("."):
        value = getattr(value, name, _MISSING)
        if value is _MISSING:
            raise AnswerError(
                f"{what} is missing. Submit EstimatorOptions or SamplerOptions objects, got {type(options).__name__}."
            )
    return plain(value)
