"""Unit tests for tron.stringify."""

from __future__ import annotations

import math

import pytest

from tron import stringify


# ============================================================
# SIMPLE SCENARIOS
# ============================================================


class TestPrimitives:
    """Primitives should serialise without a header block."""

    def test_none(self):
        assert stringify(None) == "null"

    def test_true(self):
        assert stringify(True) == "true"

    def test_false(self):
        assert stringify(False) == "false"

    def test_zero(self):
        assert stringify(0) == "0"

    def test_positive_int(self):
        assert stringify(42) == "42"

    def test_negative_int(self):
        assert stringify(-7) == "-7"

    def test_large_int(self):
        assert stringify(10**30) == str(10**30)

    def test_float(self):
        result = stringify(3.14)
        assert float(result) == pytest.approx(3.14)

    def test_negative_float(self):
        result = stringify(-0.5)
        assert float(result) == pytest.approx(-0.5)

    def test_scientific_float(self):
        result = stringify(1.23e10)
        assert float(result) == pytest.approx(1.23e10)

    def test_empty_string(self):
        assert stringify("") == '""'

    def test_simple_string(self):
        assert stringify("hello") == '"hello"'

    def test_empty_list(self):
        assert stringify([]) == "[]"

    def test_empty_dict(self):
        assert stringify({}) == "{}"

    def test_primitive_list(self):
        assert stringify([1, 2, 3]) == "[1,2,3]"

    def test_bool_list(self):
        assert stringify([True, False]) == "[true,false]"

    def test_none_in_list(self):
        assert stringify([None, None]) == "[null,null]"

    def test_no_header_for_primitive(self):
        """Primitive-only values should produce no header block."""
        assert "\n\n" not in stringify(42)
        assert "\n\n" not in stringify("hello")
        assert "\n\n" not in stringify([1, 2, 3])


class TestSimpleObject:
    def test_single_field(self):
        result = stringify({"x": 1})
        assert "class A: x" in result
        assert "A(1)" in result

    def test_two_fields(self):
        result = stringify({"a": 1, "b": 2})
        assert "class A: a,b" in result
        assert "A(1,2)" in result

    def test_string_value(self):
        result = stringify({"name": "Alice"})
        assert 'A("Alice")' in result

    def test_bool_value(self):
        result = stringify({"active": True, "deleted": False})
        assert "true" in result
        assert "false" in result

    def test_null_value(self):
        result = stringify({"email": None})
        assert "null" in result

    def test_header_body_separator(self):
        """Header and body MUST be separated by exactly one blank line."""
        result = stringify({"a": 1})
        parts = result.split("\n\n", 1)
        assert len(parts) == 2
        assert parts[0].startswith("class ")
        assert parts[1]  # body is non-empty

    def test_empty_dict_no_class(self):
        """Empty dict should not generate a class definition."""
        result = stringify({})
        assert "class" not in result
        assert result == "{}"


class TestArrayOfObjects:
    def test_uniform_array_single_class(self):
        data = [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
        result = stringify(data)
        assert "class A: x,y" in result
        assert "A(1,2)" in result
        assert "A(3,4)" in result
        # Only one class for two identical shapes
        assert result.count("class ") == 1

    def test_class_reused_across_many_instances(self):
        data = [{"k": f"v{i}"} for i in range(20)]
        result = stringify(data)
        assert result.count("class ") == 1
        assert result.count("A(") == 20

    def test_array_of_single_item_objects(self):
        data = [{"id": 1}, {"id": 2}]
        result = stringify(data)
        assert "class A: id" in result


# ============================================================
# MEDIUM SCENARIOS
# ============================================================


class TestNestedObjects:
    def test_two_level_nesting(self):
        data = {"user": {"name": "Bob", "age": 30}}
        result = stringify(data)
        # Outer dict + inner dict = 2 classes
        assert result.count("class ") == 2

    def test_three_level_nesting(self):
        data = {"a": {"b": {"c": 1}}}
        result = stringify(data)
        assert result.count("class ") == 3

    def test_object_with_nested_array_of_objects(self):
        data = {
            "items": [
                {"id": 1, "value": "a"},
                {"id": 2, "value": "b"},
            ]
        }
        result = stringify(data)
        assert result.count("class ") == 2

    def test_multiple_different_shapes(self):
        data = [
            {"name": "Alice", "role": "dev"},
            {"host": "localhost", "port": 5432},
        ]
        result = stringify(data)
        assert result.count("class ") == 2


class TestClassNaming:
    def test_first_class_is_a(self):
        data = {"x": 1}
        assert "class A:" in stringify(data)

    def test_classes_named_in_discovery_order(self):
        data = [{"x": 1}, {"y": 2}, {"z": 3}]
        result = stringify(data)
        assert "class A: x" in result
        assert "class B: y" in result
        assert "class C: z" in result

    def test_beyond_z_uses_aa(self):
        """The 27th unique shape should get class name AA."""
        data = [{f"field_{i}": i} for i in range(27)]
        result = stringify(data)
        assert "class Z:" in result
        assert "class AA:" in result

    def test_aa_ab_naming(self):
        """Classes 26 and 27 (0-indexed) should be AA and AB."""
        from tron._utils import class_name_from_index

        assert class_name_from_index(0) == "A"
        assert class_name_from_index(25) == "Z"
        assert class_name_from_index(26) == "AA"
        assert class_name_from_index(27) == "AB"
        assert class_name_from_index(51) == "AZ"
        assert class_name_from_index(52) == "BA"


class TestValueTypes:
    def test_float_in_object(self):
        result = stringify({"lat": 51.5074, "lng": -0.1278})
        assert "51.5074" in result

    def test_mixed_value_types(self):
        data = {"score": 99, "active": True, "label": None, "name": "X"}
        result = stringify(data)
        assert "99" in result
        assert "true" in result
        assert "null" in result
        assert '"X"' in result

    def test_nested_array_value(self):
        data = {"tags": ["a", "b", "c"]}
        result = stringify(data)
        assert '["a","b","c"]' in result


# ============================================================
# COMPLEX SCENARIOS
# ============================================================


class TestComplexStructures:
    def test_deeply_nested_five_levels(self):
        data = {"a": {"b": {"c": {"d": {"e": 42}}}}}
        result = stringify(data)
        assert "42" in result
        assert result.count("class ") == 5

    def test_large_uniform_array_one_class(self):
        data = [{"id": i, "name": f"u{i}", "active": i % 2 == 0} for i in range(100)]
        result = stringify(data)
        assert result.count("class ") == 1

    def test_rag_document_chunks(self):
        data = {
            "chunks": [
                {
                    "id": "doc1_chunk1",
                    "text": "LLMs are transforming AI.",
                    "metadata": {"source": "doc.pdf", "page": 1, "score": 0.95},
                },
                {
                    "id": "doc1_chunk2",
                    "text": "Token efficiency matters.",
                    "metadata": {"source": "doc.pdf", "page": 2, "score": 0.87},
                },
            ]
        }
        result = stringify(data)
        # 3 classes: wrapper, chunk, metadata
        assert result.count("class ") == 3
        assert "0.95" in result
        assert "doc.pdf" in result

    def test_time_series_data(self):
        data = {
            "metrics": [
                {"ts": "2024-01-01T00:00:00Z", "value": 42.5, "status": "ok"},
                {"ts": "2024-01-01T01:00:00Z", "value": 43.1, "status": "ok"},
                {"ts": "2024-01-01T02:00:00Z", "value": 41.8, "status": "warning"},
            ]
        }
        result = stringify(data)
        assert result.count("class ") == 2
        assert "42.5" in result
        assert "warning" in result

    def test_few_shot_examples(self):
        data = {
            "examples": [
                {"input": "Great!", "output": "positive"},
                {"input": "Terrible.", "output": "negative"},
                {"input": "Okay.", "output": "neutral"},
            ]
        }
        result = stringify(data)
        assert result.count("class ") == 2

    def test_log_data(self):
        data = {
            "logs": [
                {"level": "INFO", "ts": "2024-01-15T10:00:00Z", "msg": "Started", "uid": None},
                {"level": "WARN", "ts": "2024-01-15T10:05:00Z", "msg": "High mem", "uid": 1234},
                {"level": "ERROR", "ts": "2024-01-15T10:10:00Z", "msg": "DB down", "uid": 5678},
            ]
        }
        result = stringify(data)
        assert result.count("class ") == 2

    def test_config_file(self):
        data = {
            "app": {
                "name": "MyApp",
                "version": "1.0.0",
                "debug": False,
                "server": {"host": "0.0.0.0", "port": 8080, "timeout": 30},
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "name": "mydb",
                    "pool": {"min": 2, "max": 10},
                },
            }
        }
        result = stringify(data)
        assert "MyApp" in result
        assert "localhost" in result


# ============================================================
# ERROR CASES
# ============================================================


class TestStringifyErrors:
    def test_bytes_raises_typeerror(self):
        with pytest.raises(TypeError, match="bytes"):
            stringify(b"hello")

    def test_bytes_in_nested_object_raises(self):
        with pytest.raises(TypeError, match="bytes"):
            stringify({"data": b"binary"})

    def test_key_with_comma_raises(self):
        with pytest.raises(ValueError, match="comma"):
            stringify({"a,b": 1})

    def test_key_with_newline_raises(self):
        with pytest.raises(ValueError, match="newline"):
            stringify({"a\nb": 1})

    def test_unknown_type_raises(self):
        class Custom:
            pass

        with pytest.raises(TypeError, match="not TRON-serializable"):
            stringify(Custom())
