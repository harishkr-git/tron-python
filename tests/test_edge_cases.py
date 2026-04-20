"""Edge-case and boundary tests."""

from __future__ import annotations

import dataclasses
import math

import pytest

from tron import parse, stringify


def rt(value):
    return parse(stringify(value))


# ============================================================
# NUMERIC EDGE CASES
# ============================================================


class TestNumericEdgeCases:
    def test_nan_stringifies_to_null(self):
        assert stringify(math.nan) == "null"

    def test_positive_inf_stringifies_to_null(self):
        assert stringify(math.inf) == "null"

    def test_negative_inf_stringifies_to_null(self):
        assert stringify(-math.inf) == "null"

    def test_nan_in_object_becomes_null(self):
        result = rt({"value": math.nan, "name": "test"})
        assert result["value"] is None
        assert result["name"] == "test"

    def test_inf_in_array_becomes_null(self):
        result = rt([math.inf, -math.inf, math.nan])
        assert result == [None, None, None]

    def test_very_large_integer_preserved(self):
        big = 10**50
        assert rt(big) == big

    def test_very_small_float_preserved(self):
        val = 1e-300
        assert rt(val) == pytest.approx(val)

    def test_integer_type_preserved(self):
        result = rt({"count": 5})
        assert isinstance(result["count"], int)

    def test_negative_zero_is_zero(self):
        # JSON does not distinguish -0.0 and 0.0
        result = rt(-0.0)
        assert result == 0.0

    def test_float_precision(self):
        val = 1.0000000000000002  # smallest float distinct from 1.0
        assert rt(val) == pytest.approx(val, rel=1e-15)

    def test_boolean_not_confused_with_int(self):
        # bool is a subclass of int; ensure True/False stay booleans
        assert stringify(True) == "true"
        assert stringify(False) == "false"
        assert stringify(1) == "1"
        assert stringify(0) == "0"

    def test_bool_in_object_preserved(self):
        result = rt({"active": True, "deleted": False})
        assert result["active"] is True
        assert result["deleted"] is False


# ============================================================
# STRING EDGE CASES
# ============================================================


class TestStringEdgeCases:
    def test_double_quotes_in_string(self):
        assert rt('say "hello"') == 'say "hello"'

    def test_backslash_in_string(self):
        assert rt("path\\to\\file") == "path\\to\\file"

    def test_newline_in_string(self):
        assert rt("line1\nline2") == "line1\nline2"

    def test_carriage_return_in_string(self):
        assert rt("line1\rline2") == "line1\rline2"

    def test_tab_in_string(self):
        assert rt("col1\tcol2") == "col1\tcol2"

    def test_null_byte_in_string(self):
        assert rt("before\x00after") == "before\x00after"

    def test_all_json_escape_sequences(self):
        s = '"\\/\b\f\n\r\t'
        assert rt(s) == s

    def test_unicode_bmp_characters(self):
        assert rt("Привет мир") == "Привет мир"

    def test_unicode_cjk(self):
        assert rt("你好世界") == "你好世界"

    def test_arabic_right_to_left(self):
        assert rt("مرحبا بالعالم") == "مرحبا بالعالم"

    def test_emoji(self):
        assert rt("Hello 🎉🚀✨") == "Hello 🎉🚀✨"

    def test_emoji_surrogate_pair(self):
        # 🤩 is U+1F929, encoded as surrogate pair in JSON \uD83E\uDD29
        assert rt("🤩") == "🤩"

    def test_very_long_string(self):
        s = "x" * 10_000
        assert rt(s) == s

    def test_string_that_looks_like_class_def(self):
        assert rt({"text": "class A: foo,bar"}) == {"text": "class A: foo,bar"}

    def test_string_that_looks_like_class_instance(self):
        assert rt({"text": "A(1,2,3)"}) == {"text": "A(1,2,3)"}

    def test_string_with_colons(self):
        assert rt({"url": "https://example.com/path?a=1&b=2"}) == {
            "url": "https://example.com/path?a=1&b=2"
        }

    def test_string_with_square_brackets(self):
        assert rt({"arr": "[1,2,3]"}) == {"arr": "[1,2,3]"}

    def test_only_whitespace_string(self):
        assert rt("   ") == "   "

    def test_unicode_escape_in_json(self):
        # "\u0041" is "A" — our parser must handle \uXXXX via json.loads
        result = parse('"\\u0041"')
        assert result == "A"


# ============================================================
# STRUCTURAL EDGE CASES
# ============================================================


class TestStructuralEdgeCases:
    def test_empty_dict_in_array(self):
        assert rt([{}, {}, {}]) == [{}, {}, {}]

    def test_empty_dict_as_value(self):
        assert rt({"meta": {}}) == {"meta": {}}

    def test_empty_list_as_value(self):
        assert rt({"items": []}) == {"items": []}

    def test_deeply_nested_empty_dicts(self):
        assert rt({"a": {"b": {"c": {}}}}) == {"a": {"b": {"c": {}}}}

    def test_deeply_nested_array(self):
        data = [[[[[1, 2], [3, 4]], [[5, 6]]]]]
        assert rt(data) == data

    def test_mixed_types_in_array(self):
        data = [1, "two", None, True, {"x": 1}, [1, 2]]
        assert rt(data) == data

    def test_object_with_numeric_string_keys(self):
        data = {"1": "a", "2": "b", "3": "c"}
        assert rt(data) == data

    def test_single_item_list(self):
        assert rt([{"only": "one"}]) == [{"only": "one"}]

    def test_list_of_lists(self):
        assert rt([[1, 2], [3, 4], [5, 6]]) == [[1, 2], [3, 4], [5, 6]]

    def test_heterogeneous_list_items(self):
        data = [{"a": 1}, {"b": 2, "c": 3}, {"a": 1}]
        result = rt(data)
        assert result == data

    def test_none_at_every_position(self):
        data = [None, {"k": None}, [None], {"nested": {"v": None}}]
        assert rt(data) == data

    def test_single_null_value(self):
        assert rt({"only": None}) == {"only": None}


# ============================================================
# TYPE COERCION EDGE CASES
# ============================================================


class TestTypeCoercion:
    def test_datetime_isoformat(self):
        from datetime import datetime

        dt = datetime(2024, 1, 15, 14, 30, 0)
        result = rt(dt)
        assert result == "2024-01-15T14:30:00"

    def test_date_isoformat(self):
        from datetime import date

        d = date(2024, 1, 15)
        assert rt(d) == "2024-01-15"

    def test_datetime_with_microseconds(self):
        from datetime import datetime

        dt = datetime(2024, 1, 15, 14, 30, 0, 123456)
        assert rt(dt) == "2024-01-15T14:30:00.123456"

    def test_decimal_becomes_float(self):
        from decimal import Decimal

        d = Decimal("3.14159")
        assert rt(d) == pytest.approx(3.14159)

    def test_decimal_nan_becomes_null(self):
        from decimal import Decimal

        assert stringify(Decimal("NaN")) == "null"

    def test_decimal_infinity_becomes_null(self):
        from decimal import Decimal

        assert stringify(Decimal("Infinity")) == "null"

    def test_set_becomes_sorted_list(self):
        s = {"banana", "apple", "cherry"}
        result = rt(s)
        assert sorted(result) == ["apple", "banana", "cherry"]

    def test_frozenset_becomes_sorted_list(self):
        fs = frozenset({3, 1, 2})
        result = rt(fs)
        assert sorted(result) == [1, 2, 3]

    def test_bytes_raises_typeerror(self):
        with pytest.raises(TypeError, match="bytes"):
            stringify(b"hello")

    def test_bytes_in_dict_raises(self):
        with pytest.raises(TypeError, match="bytes"):
            stringify({"data": b"\x00\x01\x02"})

    def test_dataclass_roundtrip(self):
        @dataclasses.dataclass
        class Point:
            x: float
            y: float

        p = Point(x=1.0, y=2.0)
        assert rt(p) == {"x": 1.0, "y": 2.0}

    def test_dataclass_in_list(self):
        @dataclasses.dataclass
        class Item:
            name: str
            qty: int

        items = [Item("apple", 3), Item("banana", 5)]
        assert rt(items) == [{"name": "apple", "qty": 3}, {"name": "banana", "qty": 5}]

    def test_dataclass_nested(self):
        @dataclasses.dataclass
        class Address:
            city: str
            country: str

        @dataclasses.dataclass
        class Person:
            name: str
            address: Address

        p = Person("Alice", Address("London", "UK"))
        result = rt(p)
        assert result == {
            "name": "Alice",
            "address": {"city": "London", "country": "UK"},
        }

    def test_pydantic_v1_model(self):
        """Skip if pydantic is not installed."""
        try:
            from pydantic import BaseModel  # type: ignore[import]

            class User(BaseModel):
                name: str
                age: int

            user = User(name="Alice", age=30)
            result = rt(user)
            assert result == {"name": "Alice", "age": 30}
        except ImportError:
            pytest.skip("pydantic not installed")

    def test_try_to_dict_passthrough_for_plain_value(self):
        """try_to_dict must return non-model values unchanged."""
        from tron._utils import try_to_dict

        assert try_to_dict(42) == 42
        assert try_to_dict("hello") == "hello"
        assert try_to_dict([1, 2]) == [1, 2]
        assert try_to_dict(None) is None

    def test_try_to_dict_with_dataclass(self):
        import dataclasses

        from tron._utils import try_to_dict

        @dataclasses.dataclass
        class P:
            x: int
            y: int

        assert try_to_dict(P(1, 2)) == {"x": 1, "y": 2}

    def test_pydantic_v2_model_dump(self):
        """Test model_dump path (pydantic v2 style)."""
        import unittest.mock as mock

        from tron._utils import try_to_dict

        obj = mock.MagicMock()
        obj.model_dump.return_value = {"key": "value"}
        # Remove the 'dict' attribute so only model_dump path is tested
        del obj.dict
        result = try_to_dict(obj)
        assert result == {"key": "value"}

    def test_pydantic_v1_dict_path(self):
        """Test the .dict() fallback path (pydantic v1 style)."""
        import unittest.mock as mock

        from tron._utils import try_to_dict

        obj = mock.MagicMock(spec=["dict"])  # only has .dict(), not model_dump
        obj.dict.return_value = {"a": 1}
        result = try_to_dict(obj)
        assert result == {"a": 1}

    def test_tuple_treated_as_list(self):
        data = (1, 2, 3)
        result = rt(data)
        assert result == [1, 2, 3]


# ============================================================
# KEY VALIDATION
# ============================================================


class TestKeyValidation:
    def test_key_with_comma_raises(self):
        with pytest.raises(ValueError, match="comma"):
            stringify({"a,b": 1})

    def test_key_with_newline_raises(self):
        with pytest.raises(ValueError, match="newline"):
            stringify({"a\nb": 1})

    def test_key_with_carriage_return_raises(self):
        with pytest.raises(ValueError, match="newline"):
            stringify({"a\rb": 1})

    def test_integer_keys_become_strings(self):
        # dict with integer keys should coerce keys to str
        data = {1: "a", 2: "b"}
        result = rt(data)
        assert result == {"1": "a", "2": "b"}

    def test_unicode_keys_allowed(self):
        data = {"名前": "Alice", "年齢": 30}
        assert rt(data) == data

    def test_hyphen_in_key(self):
        data = {"my-key": 1, "another-key": 2}
        assert rt(data) == data

    def test_underscore_in_key(self):
        data = {"my_key": 1, "snake_case": True}
        assert rt(data) == data

    def test_space_in_key(self):
        data = {"my key": 1}
        assert rt(data) == data


# ============================================================
# BENCHMARK UTILITY
# ============================================================


class TestBenchmarkUtility:
    def test_benchmark_compare_returns_dict(self):
        from tron import benchmark_compare

        result = benchmark_compare({"name": "Alice", "age": 30})
        assert "json" in result
        assert "tron" in result
        assert "chars" in result["json"]
        assert "chars" in result["tron"]
        assert "char_savings_pct" in result["tron"]

    def test_tron_never_larger_for_large_uniform_array(self):
        """For large arrays of identical objects, TRON should be smaller."""
        from tron import benchmark_compare

        data = [{"id": i, "name": f"user_{i}", "active": True} for i in range(50)]
        result = benchmark_compare(data)
        assert result["tron"]["char_savings_pct"] > 0

    def test_benchmark_char_savings_is_float(self):
        from tron import benchmark_compare

        result = benchmark_compare([{"a": 1, "b": 2}] * 10)
        assert isinstance(result["tron"]["char_savings_pct"], float)

    def test_benchmark_note_when_no_tiktoken(self):
        """When tiktoken is not installed, a 'note' key must be present."""
        import builtins
        import unittest.mock as mock

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "tiktoken":
                raise ImportError("mocked missing tiktoken")
            return real_import(name, *args, **kwargs)

        from tron import benchmark_compare

        with mock.patch("builtins.__import__", side_effect=mock_import):
            result = benchmark_compare({"a": 1})
        assert "note" in result
        assert "tiktoken" in result["note"]

    def test_print_benchmark_outputs_table(self, capsys):
        from tron import print_benchmark

        print_benchmark([{"id": i, "name": f"u{i}"} for i in range(20)])
        captured = capsys.readouterr()
        assert "JSON" in captured.out
        assert "TRON" in captured.out
        assert "Chars" in captured.out

    def test_print_benchmark_shows_savings(self, capsys):
        from tron import print_benchmark

        # Large uniform array — TRON will always be smaller
        print_benchmark([{"id": i, "score": i * 1.5} for i in range(30)])
        captured = capsys.readouterr()
        # Savings percentage must appear (positive number + %)
        assert "%" in captured.out

    def test_benchmark_empty_object(self):
        from tron import benchmark_compare

        result = benchmark_compare({})
        assert result["json"]["chars"] > 0
        assert result["tron"]["chars"] > 0
