"""tron-python — Python SDK for the TRON (Token Reduced Object Notation) format.

TRON is a JSON superset that reduces token usage when sending structured data
to Large Language Models (LLMs).  It hoists repeated object schemas into a
compact class-definition header and replaces object literals with instantiation
syntax in the body — preserving full JSON compatibility for the data section.

Quick start
-----------
>>> import tron
>>> data = [{"name": "Alice", "role": "eng"}, {"name": "Bob", "role": "mktg"}]
>>> print(tron.stringify(data))
class A: name,role

[A("Alice","eng"),A("Bob","mktg")]
>>> tron.parse(tron.stringify(data)) == data
True

See https://tron-format.github.io/ for the format specification.
"""

from __future__ import annotations

from ._benchmark import benchmark_compare, print_benchmark
from ._parse import parse
from ._stringify import stringify

__all__ = [
    "stringify",
    "parse",
    "benchmark_compare",
    "print_benchmark",
    "__version__",
]

__version__ = "0.1.0"
