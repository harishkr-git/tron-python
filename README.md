# tron-python

[![CI](https://github.com/harishkr-git/tron-python/actions/workflows/ci.yml/badge.svg)](https://github.com/harishkr-git/tron-python/actions)
[![PyPI](https://img.shields.io/pypi/v/tron-python)](https://pypi.org/project/tron-python/)
[![Python](https://img.shields.io/pypi/pyversions/tron-python)](https://pypi.org/project/tron-python/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Python SDK for the **TRON (Token Reduced Object Notation)** format — a compact,
LLM-friendly superset of JSON that reduces token usage by 20–40 % by hoisting
repeated object schemas into a class-definition header.

> See the full specification at [tron-format.github.io](https://tron-format.github.io/).

---

## Why TRON?

When sending structured data to LLMs you pay per token.  JSON repeats key names
for every object in an array:

```json
[
  {"name": "Alice", "role": "eng", "active": true},
  {"name": "Bob",   "role": "mktg","active": false}
]
```

TRON defines the schema once and uses compact instantiation syntax in the body:

```
class A: name,role,active

[A("Alice","eng",true),A("Bob","mktg",false)]
```

**Same data, fewer tokens.**  TRON is a JSON *superset* — the body section is
valid JSON extended with `ClassName(arg, …)` syntax, so existing JSON parsers
can read the data without modification.

---

## Installation

```bash
pip install tron-python
```

No runtime dependencies.  Requires Python 3.9+.

Optional extras:

```bash
pip install tron-python[benchmark]   # adds tiktoken for token-count comparisons
pip install tron-python[pydantic]    # explicit pydantic dependency pin
```

---

## Quick start

```python
import tron

# Serialize
data = [
    {"name": "Alice", "role": "eng", "score": 9.5},
    {"name": "Bob",   "role": "mktg","score": 8.1},
    {"name": "Carol", "role": "eng", "score": 9.2},
]
text = tron.stringify(data)
print(text)
# class A: name,role,score
#
# [A("Alice","eng",9.5),A("Bob","mktg",8.1),A("Carol","eng",9.2)]

# Deserialize
result = tron.parse(text)
assert result == data          # True — lossless roundtrip

# Plain JSON passthrough (TRON is a superset)
assert tron.parse('[1, 2, 3]') == [1, 2, 3]
```

---

## API reference

### `tron.stringify(value) → str`

Serialize any Python value to TRON.

| Input type             | Output                              |
|------------------------|-------------------------------------|
| `None`                 | `null`                              |
| `bool`                 | `true` / `false`                    |
| `int`, `float`         | JSON number (`NaN`/`Inf` → `null`) |
| `str`                  | JSON-quoted string                  |
| `list`, `tuple`        | JSON array                          |
| `dict`                 | `ClassName(v1,v2,…)` with header    |
| `datetime`, `date`     | ISO-8601 string                     |
| `Decimal`              | float (`NaN`/`Inf` → `null`)        |
| `set`, `frozenset`     | sorted JSON array                   |
| `dataclass`, Pydantic  | converted to `dict` first           |

**Raises** `TypeError` for `bytes` or unknown types.  
**Raises** `ValueError` if a dict key contains a comma or newline.

### `tron.parse(text) → Any`

Deserialize a TRON (or plain JSON) string.

**Raises** `TypeError` if `text` is not a `str`.  
**Raises** `ValueError` for malformed TRON/JSON.

### `tron.benchmark_compare(value) → dict`

Return character and (optionally) token counts for JSON vs TRON.

```python
import tron

data = [{"id": i, "name": f"user_{i}"} for i in range(100)]
info = tron.benchmark_compare(data)
# {
#   "json": {"chars": 2890},
#   "tron": {"chars": 1750, "char_savings_pct": 39.4},
#   "note": "Install tiktoken for token-count comparisons: pip install tiktoken"
# }
```

### `tron.print_benchmark(value)`

Pretty-print a comparison table to stdout (convenience wrapper around
`benchmark_compare`).

---

## Format primer

A TRON document has two sections separated by a **blank line**:

```
class A: field1,field2   ← header: one class per unique object shape
class B: x,y,z

A("val1",42)             ← body: JSON with class instantiation
```

- Any valid JSON is valid TRON (no header required for primitive/array values).
- Class names are uppercase letters: A–Z, then AA, AB, …
- Nested objects produce nested class instantiations: `A("hello",B(1,2))`.
- The body uses standard JSON encoding for all values inside `()`.

---

## Supported Python versions

Python 3.9, 3.10, 3.11, 3.12 (tested in CI).

---

## Development

```bash
git clone https://github.com/tron-format/tron-python
cd tron-python
pip install -e ".[dev]"

# Run the full test suite
pytest

# With coverage
pytest --cov=tron --cov-report=term-missing

# Lint
ruff check src tests

# Type-check
mypy src
```

### Project layout

```
tron-python/
├── src/tron/
│   ├── __init__.py      Public API
│   ├── _stringify.py    Two-pass serializer
│   ├── _parse.py        Recursive-descent parser
│   ├── _benchmark.py    Benchmark utilities
│   ├── _utils.py        Shared helpers
│   └── py.typed         PEP 561 marker
├── tests/
│   ├── test_stringify.py
│   ├── test_parse.py
│   ├── test_roundtrip.py
│   └── test_edge_cases.py
└── pyproject.toml
```

---

## Contributing

1. Fork the repo and create a feature branch.
2. Write tests before code — all new behaviour must be covered.
3. Run `ruff check`, `mypy src`, and `pytest` before opening a PR.
4. Follow [Conventional Commits](https://www.conventionalcommits.org/) for
   commit messages.

Please open an issue before starting work on a significant change so we can
align on the approach.

---

## Acknowledgements

TRON was created by [Tim Huang](https://github.com/tron-format).  
See the [official specification](https://tron-format.github.io/) and the
[reference JavaScript SDK](https://github.com/tron-format/tron-javascript).

---

## License

MIT — see [LICENSE](LICENSE).
