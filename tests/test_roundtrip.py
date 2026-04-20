"""Roundtrip tests: stringify(x) → parse → must reproduce x."""

from __future__ import annotations

import pytest

from tron import parse, stringify


def rt(value):
    """Roundtrip helper."""
    return parse(stringify(value))


# ============================================================
# PRIMITIVES
# ============================================================


class TestRoundtripPrimitives:
    def test_none(self):
        assert rt(None) is None

    def test_true(self):
        assert rt(True) is True

    def test_false(self):
        assert rt(False) is False

    def test_zero(self):
        assert rt(0) == 0

    def test_positive_int(self):
        assert rt(42) == 42

    def test_negative_int(self):
        assert rt(-100) == -100

    def test_large_int(self):
        big = 10**50
        assert rt(big) == big

    def test_float(self):
        assert rt(3.14) == pytest.approx(3.14)

    def test_negative_float(self):
        assert rt(-2.718) == pytest.approx(-2.718)

    def test_empty_string(self):
        assert rt("") == ""

    def test_simple_string(self):
        assert rt("hello world") == "hello world"

    def test_empty_list(self):
        assert rt([]) == []

    def test_empty_dict(self):
        assert rt({}) == {}


# ============================================================
# SIMPLE
# ============================================================


class TestRoundtripSimple:
    def test_flat_object(self):
        data = {"name": "Alice", "age": 30, "active": True}
        assert rt(data) == data

    def test_primitive_array(self):
        assert rt([1, 2, 3, 4, 5]) == [1, 2, 3, 4, 5]

    def test_string_array(self):
        assert rt(["a", "b", "c"]) == ["a", "b", "c"]

    def test_array_of_objects(self):
        data = [{"id": 1, "val": "a"}, {"id": 2, "val": "b"}]
        assert rt(data) == data

    def test_mixed_primitive_array(self):
        data = [1, "two", None, True, False]
        assert rt(data) == data

    def test_nested_object(self):
        data = {"user": {"name": "Bob", "scores": [10, 20, 30]}}
        assert rt(data) == data

    def test_object_with_array_of_primitives(self):
        data = {"tags": ["python", "tron", "llm"], "ids": [1, 2, 3]}
        assert rt(data) == data

    def test_object_with_null_values(self):
        data = {"a": None, "b": None, "c": None}
        assert rt(data) == data

    def test_all_falsy_values(self):
        data = {"n": None, "f": False, "z": 0, "s": "", "l": []}
        assert rt(data) == data


# ============================================================
# MEDIUM
# ============================================================


class TestRoundtripMedium:
    def test_api_response(self):
        data = {
            "status": "ok",
            "code": 200,
            "data": {"userId": 42, "premium": True, "balance": 1234.56},
            "errors": [],
        }
        assert rt(data) == data

    def test_rag_chunks(self):
        data = {
            "chunks": [
                {"id": "c1", "text": "First chunk.", "score": 0.95},
                {"id": "c2", "text": "Second chunk.", "score": 0.87},
            ]
        }
        assert rt(data) == data

    def test_time_series(self):
        data = {
            "metrics": [
                {"ts": "2024-01-01T00:00:00Z", "v": 42.5, "ok": True},
                {"ts": "2024-01-01T01:00:00Z", "v": 43.1, "ok": True},
                {"ts": "2024-01-01T02:00:00Z", "v": 41.8, "ok": False},
            ]
        }
        assert rt(data) == data

    def test_few_shot_prompts(self):
        data = {
            "examples": [
                {"input": "Great product!", "output": "positive"},
                {"input": "Terrible service.", "output": "negative"},
                {"input": "It's okay.", "output": "neutral"},
            ]
        }
        assert rt(data) == data

    def test_config_file(self):
        data = {
            "app": {
                "name": "MyApp",
                "version": "1.0.0",
                "debug": False,
                "server": {"host": "0.0.0.0", "port": 8080},
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "pool": {"min": 2, "max": 10},
                },
            }
        }
        assert rt(data) == data

    def test_log_data(self):
        data = {
            "logs": [
                {
                    "level": "INFO",
                    "ts": "2024-01-15T10:00:00Z",
                    "msg": "Start",
                    "uid": None,
                },
                {
                    "level": "WARN",
                    "ts": "2024-01-15T10:05:00Z",
                    "msg": "Mem high",
                    "uid": 1234,
                },
                {
                    "level": "ERROR",
                    "ts": "2024-01-15T10:10:00Z",
                    "msg": "DB down",
                    "uid": 5678,
                },
            ]
        }
        assert rt(data) == data

    def test_function_calling_schema(self):
        data = {
            "function": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "required": ["location"],
                "properties": {
                    "location": {"type": "string", "description": "City name"},
                    "units": {
                        "type": "string",
                        "default": "celsius",
                        "enum": ["celsius", "fahrenheit"],
                    },
                },
            },
        }
        assert rt(data) == data


# ============================================================
# COMPLEX
# ============================================================


class TestRoundtripComplex:
    def test_deeply_nested_six_levels(self):
        data = {"a": {"b": {"c": {"d": {"e": {"f": 42}}}}}}
        assert rt(data) == data

    def test_large_uniform_array_100_items(self):
        data = [
            {"id": i, "name": f"user_{i}", "active": i % 2 == 0, "score": i * 0.1}
            for i in range(100)
        ]
        result = rt(data)
        assert result == data

    def test_multiple_types_at_same_level(self):
        data = [
            {"name": "Alice", "role": "dev"},
            {"host": "localhost", "port": 5432},
            {"x": 1.0, "y": 2.0, "z": 3.0},
        ]
        assert rt(data) == data

    def test_nested_arrays_of_objects(self):
        data = {
            "groups": [
                {"name": "Alpha", "members": [{"id": 1}, {"id": 2}]},
                {"name": "Beta", "members": [{"id": 3}, {"id": 4}]},
            ]
        }
        assert rt(data) == data

    def test_array_of_mixed_depth_objects(self):
        data = [
            {"simple": 1},
            {"nested": {"deep": {"value": 42}}},
            {"list": [{"a": 1}, {"a": 2}]},
        ]
        assert rt(data) == data

    def test_matrix_data(self):
        data = {
            "matrix": [
                [1, 2, 3, 4, 5],
                [6, 7, 8, 9, 10],
                [11, 12, 13, 14, 15],
            ]
        }
        assert rt(data) == data

    def test_unicode_content_preserved(self):
        data = {
            "messages": [
                {"lang": "ru", "text": "Привет мир"},
                {"lang": "zh", "text": "你好世界"},
                {"lang": "ar", "text": "مرحبا بالعالم"},
                {"lang": "emoji", "text": "Hello 🎉🚀✨"},
            ]
        }
        assert rt(data) == data

    def test_special_string_chars_preserved(self):
        data = {
            "strings": [
                {"v": 'say "hello"'},
                {"v": "path\\to\\file"},
                {"v": "line1\nline2"},
                {"v": "col1\tcol2"},
                {"v": "before\x00after"},
            ]
        }
        assert rt(data) == data
