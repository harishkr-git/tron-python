"""Unit tests for tron.parse."""

from __future__ import annotations

import pytest

from tron import parse

# ============================================================
# SIMPLE SCENARIOS — pure JSON passthrough
# ============================================================


class TestPureJsonPassthrough:
    """TRON is a superset of JSON; plain JSON must parse identically."""

    def test_null(self):
        assert parse("null") is None

    def test_true(self):
        assert parse("true") is True

    def test_false(self):
        assert parse("false") is False

    def test_zero(self):
        assert parse("0") == 0

    def test_positive_int(self):
        assert parse("42") == 42

    def test_negative_int(self):
        assert parse("-7") == -7

    def test_float(self):
        assert parse("3.14") == pytest.approx(3.14)

    def test_negative_float(self):
        assert parse("-0.5") == pytest.approx(-0.5)

    def test_scientific_notation(self):
        assert parse("1.23e10") == pytest.approx(1.23e10)

    def test_empty_string(self):
        assert parse('""') == ""

    def test_simple_string(self):
        assert parse('"hello"') == "hello"

    def test_empty_array(self):
        assert parse("[]") == []

    def test_empty_object(self):
        assert parse("{}") == {}

    def test_primitive_array(self):
        assert parse("[1,2,3]") == [1, 2, 3]

    def test_plain_json_object(self):
        assert parse('{"a":1,"b":2}') == {"a": 1, "b": 2}

    def test_nested_json(self):
        assert parse('{"x":{"y":1}}') == {"x": {"y": 1}}

    def test_json_array_of_objects(self):
        data = '[{"id":1},{"id":2}]'
        assert parse(data) == [{"id": 1}, {"id": 2}]


# ============================================================
# MEDIUM SCENARIOS — class instantiation
# ============================================================


class TestClassParsing:
    def test_single_class_single_instance(self):
        tron = 'class A: name,age\n\nA("Alice",30)'
        assert parse(tron) == {"name": "Alice", "age": 30}

    def test_single_class_in_array(self):
        tron = "class A: x,y\n\n[A(1,2),A(3,4)]"
        assert parse(tron) == [{"x": 1, "y": 2}, {"x": 3, "y": 4}]

    def test_wrapper_class_with_array(self):
        tron = 'class A: users\nclass B: name,role\n\nA([B("Alice","eng"),B("Bob","mktg")])'
        result = parse(tron)
        assert result == {
            "users": [
                {"name": "Alice", "role": "eng"},
                {"name": "Bob", "role": "mktg"},
            ]
        }

    def test_nested_class_instances(self):
        tron = 'class A: id,meta\nclass B: source,page\n\nA(1,B("doc.pdf",2))'
        assert parse(tron) == {"id": 1, "meta": {"source": "doc.pdf", "page": 2}}

    def test_null_argument(self):
        tron = 'class A: name,email\n\nA("Alice",null)'
        assert parse(tron) == {"name": "Alice", "email": None}

    def test_bool_arguments(self):
        tron = 'class A: name,active,deleted\n\nA("Bob",true,false)'
        assert parse(tron) == {"name": "Bob", "active": True, "deleted": False}

    def test_float_arguments(self):
        tron = "class A: lat,lng\n\nA(51.5074,-0.1278)"
        result = parse(tron)
        assert result == pytest.approx({"lat": 51.5074, "lng": -0.1278})

    def test_negative_number_argument(self):
        tron = "class A: delta\n\nA(-42)"
        assert parse(tron) == {"delta": -42}

    def test_multiline_header(self):
        tron = "class A: x\nclass B: y\nclass C: z\n\n[A(1),B(2),C(3)]"
        result = parse(tron)
        assert result == [{"x": 1}, {"y": 2}, {"z": 3}]

    def test_array_argument(self):
        tron = "class A: name,tags\n\n" 'A("Alice",["python","tron"])'
        result = parse(tron)
        assert result == {"name": "Alice", "tags": ["python", "tron"]}

    def test_multi_letter_class_name(self):
        """Class names beyond Z (AA, AB, ...) must parse correctly."""
        tron = "class AA: val\n\nAA(99)"
        assert parse(tron) == {"val": 99}


# ============================================================
# COMPLEX SCENARIOS
# ============================================================


class TestComplexParsing:
    def test_deeply_nested_class_instances(self):
        tron = (
            "class A: outer\n"
            "class B: mid\n"
            "class C: val\n"
            "\nA(B(C(42)))"
        )
        assert parse(tron) == {"outer": {"mid": {"val": 42}}}

    def test_large_array_of_class_instances(self):
        fields = "class A: id,score\n\n"
        body = "[" + ",".join(f"A({i},{i * 0.1:.1f})" for i in range(50)) + "]"
        result = parse(fields + body)
        assert len(result) == 50
        assert result[0] == {"id": 0, "score": pytest.approx(0.0)}
        assert result[49] == {"id": 49, "score": pytest.approx(4.9)}

    def test_rag_chunks(self):
        tron = (
            "class A: chunks\n"
            "class B: id,text,score\n"
            '\nA([B("c1","First chunk.",0.95),B("c2","Second chunk.",0.87)])'
        )
        result = parse(tron)
        assert result["chunks"][0] == {
            "id": "c1",
            "text": "First chunk.",
            "score": pytest.approx(0.95),
        }

    def test_mixed_plain_and_class_objects(self):
        """Plain JSON objects and class instances can coexist in the body."""
        tron = 'class A: name\n\n[A("Alice"),{"role":"admin"}]'
        result = parse(tron)
        assert result == [{"name": "Alice"}, {"role": "admin"}]

    def test_string_containing_tron_syntax(self):
        """String values that look like TRON syntax must not be expanded."""
        tron = 'class A: text\n\nA("class B: foo")'
        assert parse(tron) == {"text": "class B: foo"}

    def test_string_with_parentheses(self):
        tron = 'class A: expr\n\nA("f(x,y)")'
        assert parse(tron) == {"expr": "f(x,y)"}


# ============================================================
# WHITESPACE / LINE-ENDING ROBUSTNESS
# ============================================================


class TestParseRobustness:
    def test_windows_crlf_line_endings(self):
        tron = "class A: x,y\r\n\r\nA(1,2)"
        assert parse(tron) == {"x": 1, "y": 2}

    def test_bare_cr_line_endings(self):
        tron = "class A: x\r\rA(1)"
        assert parse(tron) == {"x": 1}

    def test_whitespace_on_blank_separator_line(self):
        tron = "class A: x\n  \nA(1)"
        assert parse(tron) == {"x": 1}

    def test_extra_whitespace_around_field_names(self):
        tron = "class A:  x , y \n\nA(1,2)"
        assert parse(tron) == {"x": 1, "y": 2}

    def test_whitespace_between_args(self):
        tron = "class A: x,y\n\nA( 1 , 2 )"
        assert parse(tron) == {"x": 1, "y": 2}


# ============================================================
# ERROR SCENARIOS
# ============================================================


class TestParseErrors:
    def test_non_string_input_raises_typeerror(self):
        with pytest.raises(TypeError, match="str"):
            parse(42)  # type: ignore[arg-type]

    def test_none_input_raises_typeerror(self):
        with pytest.raises(TypeError):
            parse(None)  # type: ignore[arg-type]

    def test_undefined_class_raises(self):
        with pytest.raises(ValueError, match="Undefined TRON class"):
            parse("class A: x\n\nB(1)")

    def test_wrong_arg_count_raises(self):
        with pytest.raises(ValueError, match="declares 2 field"):
            parse("class A: x,y\n\nA(1)")

    def test_too_many_args_raises(self):
        with pytest.raises(ValueError, match="declares 1 field"):
            parse("class A: x\n\nA(1,2,3)")

    def test_malformed_header_raises(self):
        with pytest.raises(ValueError, match="Malformed TRON class definition"):
            parse("not a class def\n\nnull")

    def test_duplicate_class_in_header_raises(self):
        with pytest.raises(ValueError, match="Duplicate class"):
            parse("class A: x\nclass A: y\n\nA(1)")

    def test_empty_body_raises(self):
        with pytest.raises(ValueError, match="empty"):
            parse("class A: x\n\n")

    def test_trailing_content_raises(self):
        # Input must go through our custom parser (has a header + blank line),
        # otherwise json.loads handles it and gives a different message.
        with pytest.raises(ValueError, match="Unexpected trailing content"):
            parse("class A: x\n\nA(1) garbage")

    def test_plain_json_trailing_raises(self):
        # Fast-path (no header): json.loads catches trailing content
        with pytest.raises(ValueError):
            parse("null extra_garbage")

    def test_missing_open_paren_after_class_name(self):
        with pytest.raises(ValueError, match="Expected '\\(' after class name"):
            parse("class A: x\n\nA 1")

    def test_unexpected_char_in_args(self):
        with pytest.raises(ValueError, match="Expected ',' or '\\)'"):
            parse("class A: x,y\n\nA(1;2)")

    def test_unterminated_class_instantiation(self):
        # Parser hits EOF while reading a value inside the arg list
        with pytest.raises(ValueError, match="Unexpected end of TRON input"):
            parse("class A: x,y\n\nA(1,")

    def test_unexpected_token_raises(self):
        with pytest.raises(ValueError, match="Unexpected token"):
            parse("class A: x\n\n@bad")

    def test_empty_field_name_in_header_raises(self):
        with pytest.raises(ValueError, match="empty field"):
            parse("class A: x,,y\n\nA(1,2,3)")

    def test_unterminated_object_raises(self):
        # Parser hits EOF while reading the object value
        with pytest.raises(ValueError, match="Unexpected end of TRON input"):
            parse('class A: x\n\n{"key":')

    def test_unterminated_array_raises(self):
        # Parser hits EOF while reading the next array element
        with pytest.raises(ValueError, match="Unexpected end of TRON input"):
            parse("class A: x\n\n[1,2,")

    def test_unexpected_end_of_input(self):
        # Empty body is caught before the parser runs
        with pytest.raises(ValueError, match="TRON body is empty"):
            parse("class A: x\n\n")  # body is empty after strip

    def test_invalid_number_raises(self):
        with pytest.raises(ValueError):
            parse("class A: x\n\nA(-z)")

    def test_object_key_must_be_string(self):
        # Object with non-string key should fail gracefully
        with pytest.raises(ValueError):
            parse('class A: x\n\n{1:"bad"}')

    def test_unexpected_char_in_object_raises(self):
        with pytest.raises(ValueError, match="Expected ',' or '}'"):
            parse('class A: x\n\n{"k":1 "j":2}')

    def test_unexpected_char_in_array_raises(self):
        with pytest.raises(ValueError, match="Expected ',' or ']'"):
            parse("class A: x\n\n[1 2]")

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Invalid TRON"):
            parse("{bad json}")

    def test_unterminated_string_raises(self):
        with pytest.raises(ValueError, match="Unterminated string"):
            parse('"no closing quote')
