"""TRON serializer — converts Python objects to TRON-formatted strings."""

from __future__ import annotations

import json
import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from ._utils import class_name_from_index, is_finite_float, try_to_dict


# ---------------------------------------------------------------------------
# Value coercion
# ---------------------------------------------------------------------------

def _coerce(value: Any) -> Any:
    """Coerce Python-specific types to TRON-serializable primitives.

    Conversion rules
    ----------------
    * ``datetime`` / ``date`` → ISO-8601 string
    * ``Decimal``             → float (NaN / Inf → ``None``)
    * ``float`` NaN / Inf     → ``None``
    * ``set``                 → sorted list (for determinism)
    * ``bytes``               → raises ``TypeError``
    * Everything else         → unchanged
    """
    # bool must be checked before int (bool is a subclass of int)
    if isinstance(value, bool):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        f = float(value)
        return f if is_finite_float(f) else None
    if isinstance(value, float):
        return value if is_finite_float(value) else None
    if isinstance(value, frozenset):
        return sorted(value, key=str)
    if isinstance(value, set):
        return sorted(value, key=str)
    if isinstance(value, bytes):
        raise TypeError(
            "bytes is not TRON-serializable. "
            "Encode first: base64.b64encode(b).decode()"
        )
    return value


def _validate_key(key: str) -> str:
    """Ensure a dict key is safe for use in a TRON class definition."""
    if "," in key:
        raise ValueError(
            f"Object key {key!r} contains a comma, which is not allowed in "
            "TRON class definitions. Rename the key or omit it."
        )
    if "\n" in key or "\r" in key:
        raise ValueError(
            f"Object key {key!r} contains a newline, which is not allowed in "
            "TRON class definitions."
        )
    return key


# ---------------------------------------------------------------------------
# Internal stringifier
# ---------------------------------------------------------------------------

class _Stringifier:
    """Two-pass stateful TRON serializer.

    Pass 1 (``_discover``) walks the value tree and registers a class for
    every unique dict key-tuple encountered.

    Pass 2 (``_emit``) serialises the value tree, substituting
    ``ClassName(v1,v2,…)`` for every dict that has a registered class.
    """

    __slots__ = ("_registry", "_index")

    def __init__(self) -> None:
        # key_tuple → class_name, in insertion (discovery) order
        self._registry: dict[tuple[str, ...], str] = {}
        self._index: int = 0

    # ------------------------------------------------------------------
    # Pass 1 — discovery
    # ------------------------------------------------------------------

    def _ensure_class(self, key_tuple: tuple[str, ...]) -> str:
        if key_tuple not in self._registry:
            self._registry[key_tuple] = class_name_from_index(self._index)
            self._index += 1
        return self._registry[key_tuple]

    def _discover(self, value: Any) -> None:
        value = try_to_dict(value)
        value = _coerce(value)

        if isinstance(value, dict):
            keys = tuple(_validate_key(str(k)) for k in value.keys())
            if keys:  # skip empty dicts — no class needed
                self._ensure_class(keys)
            for v in value.values():
                self._discover(v)
        elif isinstance(value, (list, tuple)):
            for item in value:
                self._discover(item)
        # primitives have no children to discover

    # ------------------------------------------------------------------
    # Pass 2 — emission
    # ------------------------------------------------------------------

    def _emit(self, value: Any) -> str:
        value = try_to_dict(value)
        value = _coerce(value)

        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            if not is_finite_float(value):
                return "null"
            return json.dumps(value)
        if isinstance(value, str):
            return json.dumps(value)
        if isinstance(value, (list, tuple)):
            return "[" + ",".join(self._emit(item) for item in value) + "]"
        if isinstance(value, dict):
            keys = tuple(str(k) for k in value.keys())
            if not keys:
                return "{}"
            class_name = self._registry[keys]
            args = ",".join(self._emit(v) for v in value.values())
            return f"{class_name}({args})"

        raise TypeError(
            f"Object of type {type(value).__name__!r} is not TRON-serializable. "
            "Use a JSON-compatible type or implement a custom converter."
        )

    # ------------------------------------------------------------------
    # Entry-point
    # ------------------------------------------------------------------

    def run(self, value: Any) -> str:
        if value is None:
            return "null"

        self._discover(value)
        body = self._emit(value)

        if not self._registry:
            # No dicts in the value — emit pure JSON body with no header
            return body

        header_lines = [
            f"class {name}: {','.join(keys)}"
            for keys, name in self._registry.items()
        ]
        return "\n".join(header_lines) + "\n\n" + body


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def stringify(value: Any) -> str:
    """Serialize *value* to a TRON-formatted string.

    Mirrors the interface of ``json.dumps`` but produces TRON output: a
    compact class-definition header followed by a blank line and a JSON-like
    body where repeated object schemas are replaced by class instantiations.

    Parameters
    ----------
    value:
        The Python object to serialize.

    Returns
    -------
    str
        TRON-encoded string.  Any valid JSON is also valid TRON, so for
        values containing no dicts the output is identical to
        ``json.dumps(value, separators=(',', ':'))``.

    Raises
    ------
    TypeError
        If *value* contains a type that cannot be serialized (e.g. ``bytes``).
    ValueError
        If a dict key contains a comma or newline character.

    Examples
    --------
    >>> stringify([{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}])
    'class A: name,age\\n\\n[A("Alice",30),A("Bob",25)]'
    """
    return _Stringifier().run(value)
