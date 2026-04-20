"""Internal utilities shared across the TRON SDK."""

from __future__ import annotations

import math
from typing import Any

_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def class_name_from_index(idx: int) -> str:
    """Return the TRON class name for a zero-based index.

    Produces A, B, ..., Z, AA, AB, ..., AZ, BA, ... (base-26, bijective).
    """
    name = ""
    idx += 1  # bijective: no "zero" digit
    while idx > 0:
        idx -= 1
        name = _LETTERS[idx % 26] + name
        idx //= 26
    return name


def is_finite_float(value: float) -> bool:
    """Return True iff *value* is neither NaN nor infinite."""
    return not (math.isnan(value) or math.isinf(value))


def try_to_dict(value: Any) -> Any:
    """Best-effort conversion of Pydantic models and dataclasses to ``dict``.

    Returns *value* unchanged if it is not a recognised model type.
    """
    # Pydantic v2
    if hasattr(value, "model_dump") and callable(value.model_dump):
        try:
            return value.model_dump()
        except Exception:
            pass

    # Pydantic v1
    if hasattr(value, "dict") and callable(value.dict):
        try:
            return value.dict()
        except Exception:
            pass

    # dataclasses (stdlib)
    try:
        import dataclasses

        if dataclasses.is_dataclass(value) and not isinstance(value, type):
            return dataclasses.asdict(value)
    except ImportError:
        pass

    return value
