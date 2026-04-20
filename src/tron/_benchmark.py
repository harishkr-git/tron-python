"""Benchmark utility — compare JSON vs TRON character and token efficiency."""

from __future__ import annotations

import json
from typing import Any

from ._stringify import stringify


def benchmark_compare(value: Any) -> dict[str, Any]:
    """Compare character and (optionally) token counts for JSON vs TRON.

    Parameters
    ----------
    value:
        Any Python object that can be TRON-serialized.

    Returns
    -------
    dict
        Structure::

            {
                "json":  {"chars": int, "tokens": int},  # tokens if tiktoken installed
                "tron":  {"chars": int, "char_savings_pct": float,
                          "tokens": int, "token_savings_pct": float},
                "note":  str,  # present when tiktoken is not installed
            }

    Notes
    -----
    Token counts use the ``cl100k_base`` encoding (GPT-3.5 / GPT-4 / Claude).
    Install ``tiktoken`` to enable: ``pip install tiktoken``.
    """
    json_str = json.dumps(value, separators=(",", ":"))
    tron_str = stringify(value)

    j_chars = len(json_str)
    t_chars = len(tron_str)
    char_savings = (
        round((1 - t_chars / j_chars) * 100, 1) if j_chars > 0 else 0.0
    )

    result: dict[str, Any] = {
        "json": {"chars": j_chars},
        "tron": {"chars": t_chars, "char_savings_pct": char_savings},
    }

    try:
        import tiktoken  # type: ignore[import-not-found]

        enc = tiktoken.get_encoding("cl100k_base")
        j_tokens = len(enc.encode(json_str))
        t_tokens = len(enc.encode(tron_str))
        token_savings = (
            round((1 - t_tokens / j_tokens) * 100, 1) if j_tokens > 0 else 0.0
        )
        result["json"]["tokens"] = j_tokens
        result["tron"]["tokens"] = t_tokens
        result["tron"]["token_savings_pct"] = token_savings
    except ImportError:
        result["note"] = (
            "Install tiktoken for token-count comparisons: pip install tiktoken"
        )

    return result


def print_benchmark(value: Any) -> None:
    """Pretty-print a benchmark comparison table for *value*.

    Example output::

        ┌─────────┬────────┬────────┬──────────────────┬──────────────────┐
        │ Format  │ Chars  │ Tokens │  Char savings    │  Token savings   │
        ├─────────┼────────┼────────┼──────────────────┼──────────────────┤
        │ JSON    │    461 │    138 │              —   │              —   │
        │ TRON    │    307 │     89 │         33.4 %   │         35.5 %   │
        └─────────┴────────┴────────┴──────────────────┴──────────────────┘
    """
    info = benchmark_compare(value)
    has_tokens = "tokens" in info["json"]

    header = f"{'Format':<8} {'Chars':>8}"
    if has_tokens:
        header += f"  {'Tokens':>8}  {'Char savings':>14}  {'Token savings':>14}"
    else:
        header += f"  {'Char savings':>14}"

    sep = "─" * len(header)
    print(sep)
    print(header)
    print(sep)

    def _row(name: str, chars: int, tokens: int | None, char_s: str, tok_s: str) -> str:
        row = f"{name:<8} {chars:>8}"
        if has_tokens:
            tok_str = f"{tokens:>8}" if tokens is not None else "       —"
            row += f"  {tok_str}  {char_s:>14}  {tok_s:>14}"
        else:
            row += f"  {char_s:>14}"
        return row

    print(
        _row(
            "JSON",
            info["json"]["chars"],
            info["json"].get("tokens"),
            "—",
            "—",
        )
    )
    t = info["tron"]
    print(
        _row(
            "TRON",
            t["chars"],
            t.get("tokens"),
            f"{t['char_savings_pct']:+.1f} %",
            f"{t.get('token_savings_pct', '?'):+.1f} %" if has_tokens else "—",
        )
    )
    print(sep)
    if "note" in info:
        print(f"Note: {info['note']}")
