# Changelog

All notable changes to tron-python are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

## [0.1.0] — 2025-01-01

### Added
- `tron.stringify(value)` — serialize Python objects to TRON format
- `tron.parse(text)` — deserialize TRON (and plain JSON) strings
- `tron.benchmark_compare(value)` — compare character/token counts for JSON vs TRON
- `tron.print_benchmark(value)` — pretty-print benchmark table to stdout
- Full type annotations (PEP 561 `py.typed` marker)
- Support for `datetime`, `date`, `Decimal`, `set`, `frozenset` coercion
- Support for `dataclasses.dataclass` and Pydantic v1/v2 models
- Recursive-descent body parser — handles arbitrary nesting depth
- Class names A–Z then AA, AB, …, AZ, BA, … (bijective base-26)
- Zero runtime dependencies — stdlib only
- 90 %+ test coverage across four test modules

[Unreleased]: https://github.com/tron-format/tron-python/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/tron-format/tron-python/releases/tag/v0.1.0
