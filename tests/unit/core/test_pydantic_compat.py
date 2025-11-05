"""Unit tests for openhands.core.pydantic_compat.

These tests avoid importing Pydantic itself and instead emulate the
relevant attributes/methods so they run the same under pydantic v1, v2,
or neither installed.
"""

from openhands.core.pydantic_compat import get_model_field_names, model_to_dict


def test_model_to_dict_prefers_model_dump():

    class V2Like:

        def __init__(self):
            self.a = 1

        def model_dump(self):
            return {"a": self.a}

    assert model_to_dict(V2Like()) == {"a": 1}


def test_model_to_dict_falls_back_to_dict():

    class V1Like:

        def __init__(self):
            self.b = 2

        def dict(self):
            return {"b": self.b}

    assert model_to_dict(V1Like()) == {"b": 2}


def test_model_to_dict_passthrough_for_plain_dict():
    d = {"x": "y"}
    assert model_to_dict(d) == d


def test_get_model_field_names_prefers_model_fields():

    class V2Cls:
        model_fields = {"f1": None, "f2": None}

    assert get_model_field_names(V2Cls) == {"f1", "f2"}


def test_get_model_field_names_falls_back_to___fields__():

    class V1Cls:
        __fields__ = {"g1": None}

    assert get_model_field_names(V1Cls) == {"g1"}


def test_get_model_field_names_uses_annotations_last():

    class AnnCls:
        __annotations__ = {"h1": int}

    assert get_model_field_names(AnnCls) == {"h1"}


def test_get_model_field_names_priority_order():

    class Mixed:
        model_fields = {"a": None}
        __fields__ = {"b": None}
        __annotations__ = {"c": int}

    assert get_model_field_names(Mixed) == {"a"}
