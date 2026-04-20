"""TRON deserializer — converts TRON-formatted strings to Python objects."""

from __future__ import annotations

import json
import re
from typing import Any

# ---------------------------------------------------------------------------
# Header parsing
# ---------------------------------------------------------------------------

# Matches blank lines (with optional horizontal whitespace) that separate the
# class-definition header from the JSON body.
_BLANK_LINE_RE = re.compile(r"\n[ \t]*\n")

# Matches a single class definition line, e.g. "class AB: field1, field2"
_CLASS_DEF_RE = re.compile(r"^class\s+([A-Z]+)\s*:\s*(.+)$")


def _parse_header(header: str) -> dict[str, list[str]]:
    """Parse TRON class definitions from the header block.

    Parameters
    ----------
    header:
        The text above the first blank line in a TRON document.

    Returns
    -------
    dict
        Maps class name (e.g. ``"A"``) to an ordered list of field names.

    Raises
    ------
    ValueError
        If any line in *header* is not a valid class definition.
    """
    registry: dict[str, list[str]] = {}
    for line in header.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _CLASS_DEF_RE.match(line)
        if not m:
            raise ValueError(
                f"Malformed TRON class definition: {line!r}. "
                "Expected format: 'class <NAME>: field1,field2,...'"
            )
        class_name = m.group(1)
        fields_raw = m.group(2)
        fields = [f.strip() for f in fields_raw.split(",")]
        empty = [f for f in fields if not f]
        if empty:
            raise ValueError(
                f"Class {class_name!r} has one or more empty field names "
                f"in definition: {fields_raw!r}"
            )
        if class_name in registry:
            raise ValueError(
                f"Duplicate class definition for {class_name!r} in TRON header"
            )
        registry[class_name] = fields
    return registry


# ---------------------------------------------------------------------------
# Recursive-descent body parser
# ---------------------------------------------------------------------------


class _Parser:
    """Recursive-descent parser for the TRON body.

    The body is JSON with two extensions:

    1. ``ClassName(v1, v2, …)`` — class instantiation replacing ``{…}``.
    2. All class names defined in the header must be resolvable.

    All standard JSON types (null, true, false, numbers, strings, arrays,
    plain objects) are handled identically to ``json.loads``.
    """

    __slots__ = ("text", "pos", "registry")

    def __init__(self, text: str, registry: dict[str, list[str]]) -> None:
        self.text = text
        self.pos = 0
        self.registry = registry

    # ------------------------------------------------------------------
    # Public entry-point
    # ------------------------------------------------------------------

    def parse(self) -> Any:
        self._skip_ws()
        value = self._parse_value()
        self._skip_ws()
        if self.pos < len(self.text):
            snippet = self.text[self.pos : self.pos + 40]
            raise ValueError(
                f"Unexpected trailing content at position {self.pos}: {snippet!r}"
            )
        return value

    # ------------------------------------------------------------------
    # Core value dispatch
    # ------------------------------------------------------------------

    def _parse_value(self) -> Any:
        self._skip_ws()
        if self.pos >= len(self.text):
            raise ValueError("Unexpected end of TRON input while reading value")

        c = self.text[self.pos]

        if c.isupper():
            return self._parse_class_instance()
        if c == '"':
            return self._parse_string()
        if c == "{":
            return self._parse_object()
        if c == "[":
            return self._parse_array()
        if c == "n" and self._peek("null"):
            self.pos += 4
            return None
        if c == "t" and self._peek("true"):
            self.pos += 4
            return True
        if c == "f" and self._peek("false"):
            self.pos += 5
            return False
        if c == "-" or c.isdigit():
            return self._parse_number()

        ctx = self.text[max(0, self.pos - 10) : self.pos + 20]
        raise ValueError(
            f"Unexpected token {c!r} at position {self.pos}. Context: ...{ctx!r}..."
        )

    # ------------------------------------------------------------------
    # TRON extension: class instantiation  →  A(v1, v2, ...)
    # ------------------------------------------------------------------

    def _parse_class_instance(self) -> dict[str, Any]:
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos].isupper():
            self.pos += 1
        class_name = self.text[start : self.pos]

        if class_name not in self.registry:
            raise ValueError(
                f"Undefined TRON class {class_name!r}. "
                f"Known classes: {list(self.registry)}"
            )

        fields = self.registry[class_name]

        if self.pos >= len(self.text) or self.text[self.pos] != "(":
            got = self.text[self.pos] if self.pos < len(self.text) else "EOF"
            raise ValueError(
                f"Expected '(' after class name {class_name!r}, got {got!r}"
            )
        self.pos += 1  # consume '('
        self._skip_ws()

        args: list[Any] = []

        # Handle zero-field class (empty dict)
        if self.pos < len(self.text) and self.text[self.pos] == ")":
            self.pos += 1
        else:
            while True:
                args.append(self._parse_value())
                self._skip_ws()
                if self.pos >= len(self.text):
                    raise ValueError(
                        f"Unterminated class instantiation for {class_name!r}"
                    )
                ch = self.text[self.pos]
                if ch == ")":
                    self.pos += 1
                    break
                if ch == ",":
                    self.pos += 1
                    self._skip_ws()
                else:
                    raise ValueError(
                        f"Expected ',' or ')' inside {class_name!r}(...), "
                        f"got {ch!r} at position {self.pos}"
                    )

        if len(args) != len(fields):
            raise ValueError(
                f"Class {class_name!r} declares {len(fields)} field(s) "
                f"({', '.join(repr(f) for f in fields)}) "
                f"but received {len(args)} argument(s)"
            )

        return dict(zip(fields, args))

    # ------------------------------------------------------------------
    # JSON-compatible types
    # ------------------------------------------------------------------

    def _parse_string(self) -> str:
        """Parse a JSON-encoded string, delegating unicode escapes to json."""
        start = self.pos
        self.pos += 1  # consume opening '"'
        while self.pos < len(self.text):
            ch = self.text[self.pos]
            if ch == "\\":
                self.pos += 2  # skip escape + next char
            elif ch == '"':
                self.pos += 1  # consume closing '"'
                break
            else:
                self.pos += 1
        else:
            raise ValueError("Unterminated string in TRON input")
        # Delegate all JSON string decoding (escape sequences, unicode) to
        # the stdlib — no need to re-implement it.
        return json.loads(self.text[start : self.pos])

    def _parse_number(self) -> int | float:
        start = self.pos
        if self.text[self.pos] == "-":
            self.pos += 1
        if self.pos >= len(self.text) or not self.text[self.pos].isdigit():
            raise ValueError(
                f"Invalid number at position {self.pos}: "
                f"{self.text[start : start + 10]!r}"
            )
        self._consume_digits()
        # Fractional part
        if self.pos < len(self.text) and self.text[self.pos] == ".":
            self.pos += 1
            self._consume_digits()
        # Exponent
        if self.pos < len(self.text) and self.text[self.pos] in "eE":
            self.pos += 1
            if self.pos < len(self.text) and self.text[self.pos] in "+-":
                self.pos += 1
            self._consume_digits()
        # Delegate int vs float distinction to json.loads
        return json.loads(self.text[start : self.pos])

    def _parse_object(self) -> dict[str, Any]:
        """Parse a plain JSON object ``{…}`` (no class substitution)."""
        self._expect("{")
        result: dict[str, Any] = {}
        self._skip_ws()

        if self.pos < len(self.text) and self.text[self.pos] == "}":
            self.pos += 1
            return result

        while True:
            self._skip_ws()
            key = self._parse_string()
            self._skip_ws()
            self._expect(":")
            value = self._parse_value()
            result[key] = value
            self._skip_ws()
            if self.pos >= len(self.text):
                raise ValueError("Unterminated JSON object")
            ch = self.text[self.pos]
            if ch == "}":
                self.pos += 1
                break
            if ch == ",":
                self.pos += 1
            else:
                raise ValueError(
                    f"Expected ',' or '}}' in object, got {ch!r} at position {self.pos}"
                )

        return result

    def _parse_array(self) -> list[Any]:
        """Parse a JSON array ``[…]``; elements may be class instances."""
        self._expect("[")
        result: list[Any] = []
        self._skip_ws()

        if self.pos < len(self.text) and self.text[self.pos] == "]":
            self.pos += 1
            return result

        while True:
            result.append(self._parse_value())
            self._skip_ws()
            if self.pos >= len(self.text):
                raise ValueError("Unterminated JSON array")
            ch = self.text[self.pos]
            if ch == "]":
                self.pos += 1
                break
            if ch == ",":
                self.pos += 1
                self._skip_ws()
            else:
                raise ValueError(
                    f"Expected ',' or ']' in array, got {ch!r} at position {self.pos}"
                )

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _skip_ws(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos] in " \t\r\n":
            self.pos += 1

    def _peek(self, token: str) -> bool:
        return self.text[self.pos : self.pos + len(token)] == token

    def _expect(self, char: str) -> None:
        if self.pos >= len(self.text):
            raise ValueError(f"Expected {char!r} at position {self.pos}, got EOF")
        if self.text[self.pos] != char:
            raise ValueError(
                f"Expected {char!r} at position {self.pos}, got {self.text[self.pos]!r}"
            )
        self.pos += 1

    def _consume_digits(self) -> None:
        if self.pos >= len(self.text) or not self.text[self.pos].isdigit():
            raise ValueError(f"Expected digit at position {self.pos}")
        while self.pos < len(self.text) and self.text[self.pos].isdigit():
            self.pos += 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse(text: str) -> Any:
    """Deserialize a TRON-formatted (or plain JSON) string to a Python object.

    TRON is a superset of JSON, so any valid JSON string is accepted.  When
    a header with class definitions is present (separated from the body by a
    blank line) the class instantiations in the body are expanded into plain
    Python dicts.

    Parameters
    ----------
    text:
        A TRON or plain-JSON encoded string.

    Returns
    -------
    Any
        The deserialized Python object.

    Raises
    ------
    TypeError
        If *text* is not a ``str``.
    ValueError
        If *text* is not valid TRON / JSON.

    Examples
    --------
    >>> parse('class A: name,age\\n\\nA("Alice",30)')
    {'name': 'Alice', 'age': 30}
    >>> parse('[1, 2, 3]')  # plain JSON passthrough
    [1, 2, 3]
    """
    if not isinstance(text, str):
        raise TypeError(f"parse() expects a str, got {type(text).__name__!r}")

    # Normalise line endings so Windows CRLF and bare CR don't trip up
    # the blank-line detector.
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Split on the first blank line (header | body).
    parts = _BLANK_LINE_RE.split(text, maxsplit=1)

    if len(parts) == 1:
        # No header found → treat the entire text as plain JSON (fast path).
        try:
            return json.loads(parts[0])
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid TRON/JSON: {exc}") from exc

    header_text, body_text = parts

    # An empty header section is valid — it just means no classes were defined.
    registry = _parse_header(header_text)

    body_text = body_text.strip()
    if not body_text:
        raise ValueError("TRON body is empty after the class-definition header")

    return _Parser(body_text, registry).parse()
