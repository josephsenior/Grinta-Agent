import json
from types import SimpleNamespace

import pytest

from forge.core import pydantic_compat as compat


class V2LikeModel:
    def __init__(self, value):
        self.value = value

    def model_dump(self, **kwargs):
        return {"value": self.value, "kwargs": kwargs}

    def model_dump_json(self, **kwargs):
        return json.dumps(self.model_dump(**kwargs))


class V1LikeModel:
    def __init__(self, value):
        self.value = value

    def dict(self, **kwargs):
        return {"value": self.value, "kwargs": kwargs}

    def json(self, **kwargs):
        return json.dumps(self.dict(**kwargs))


class BrokenModel:
    def model_dump(self, **kwargs):
        raise RuntimeError("boom")

    def dict(self, **kwargs):
        raise RuntimeError("boom")


class FieldModelV2:
    model_fields = {"field": None, "other": None}


class FieldModelV1:
    __fields__ = {"legacy": None}


class FieldAnnotations:
    __annotations__ = {"annotated": int}


def test_model_to_dict_prefers_model_dump():
    model = V2LikeModel(5)
    result = compat.model_to_dict(model)
    assert result["value"] == 5


def test_model_to_dict_fallbacks_to_dict():
    model = V1LikeModel(10)
    result = compat.model_to_dict(model)
    assert result["value"] == 10


def test_model_to_dict_roundtrip_json(monkeypatch):
    obj = SimpleNamespace(custom=set([1, 2]))
    converted = compat.model_to_dict(obj)
    expected = json.loads(json.dumps(obj, default=str))
    assert converted == expected


def test_model_to_dict_handles_error_then_dict():
    class MixedModel:
        def __init__(self, value):
            self.value = value

        def model_dump(self):
            raise RuntimeError("bad dump")

        def dict(self):
            return {"value": self.value}

    result = compat.model_to_dict(MixedModel(5))
    assert result == {"value": 5}


def test_model_to_dict_returns_original_on_failure():
    class Unserializable:
        def model_dump(self):
            raise RuntimeError

        def dict(self):
            raise RuntimeError

        def __str__(self):
            raise RuntimeError

    obj = Unserializable()
    result = compat.model_to_dict(obj)
    assert result is obj


def test_get_model_field_names_all_paths():
    assert compat.get_model_field_names(FieldModelV2) == {"field", "other"}
    assert compat.get_model_field_names(FieldModelV1) == {"legacy"}
    assert compat.get_model_field_names(FieldAnnotations) == {"annotated"}


class DumpOrderModel:
    def __init__(self, value):
        self.value = value

    def model_dump(self, **kwargs):
        return {"value": self.value}


class DumpJsonModel:
    def json(self, **kwargs):
        return json.dumps({"value": 42})


class DumpDictModel:
    def dict(self, **kwargs):
        return {"value": 99, "kwargs": kwargs}


def test_model_dump_with_options_prefers_model_dump():
    model = DumpOrderModel(1)
    result = compat.model_dump_with_options(model, mode="json")
    assert result == {"value": 1}


def test_model_dump_with_options_json_path():
    model = DumpJsonModel()
    result = compat.model_dump_with_options(model, mode="json", include={"value"})
    assert result == {"value": 42}


def test_model_dump_with_options_dict_path():
    model = DumpDictModel()
    result = compat.model_dump_with_options(model, mode="dict", exclude_none=True)
    assert result["value"] == 99
    assert "kwargs" in result


def test_model_dump_with_options_fallback_to_model_to_dict(monkeypatch):
    monkeypatch.setattr(compat, "model_to_dict", lambda obj: {"fallback": True})
    result = compat.model_dump_with_options(BrokenModel())
    assert result["fallback"] is True


def test_model_dump_with_options_json_exception_path():
    class JsonRaiseModel:
        def json(self, **kwargs):
            raise RuntimeError("fail")

    result = compat.model_dump_with_options(JsonRaiseModel(), mode="json")
    assert result == compat.model_to_dict(JsonRaiseModel())


class DumpJsonFailure:
    def model_dump_json(self, **kwargs):
        raise RuntimeError("fail")

    def json(self, **kwargs):
        raise RuntimeError("fail")


def test_model_dump_json_prefers_v2():
    model = V2LikeModel(3)
    result = compat.model_dump_json(model, mode="json")
    assert json.loads(result)["value"] == 3


def test_model_dump_json_falls_back_to_json():
    model = V1LikeModel(4)
    result = compat.model_dump_json(model)
    assert json.loads(result)["value"] == 4


def test_model_dump_json_best_effort(monkeypatch):
    monkeypatch.setattr(
        compat, "model_dump_with_options", lambda obj, **kwargs: {"value": 7}
    )
    result = compat.model_dump_json(DumpJsonFailure(), mode="json")
    assert json.loads(result)["value"] == 7


def test_model_dump_json_final_fallback(monkeypatch):
    monkeypatch.setattr(
        compat,
        "model_dump_with_options",
        lambda obj, **kwargs: (_ for _ in ()).throw(RuntimeError()),
    )
    monkeypatch.setattr(compat, "model_to_dict", lambda obj: {"value": "fallback"})
    result = compat.model_dump_json(DumpJsonFailure())
    assert json.loads(result)["value"] == "fallback"


def test_get_model_field_names_handles_missing_attrs():
    class Empty:
        pass

    assert compat.get_model_field_names(Empty) == set()


def test_try_get_v2_model_fields_handles_exception():
    class Raising:
        def __get__(self, obj, objtype=None):
            raise RuntimeError

    class Model:
        model_fields = Raising()

    assert compat._try_get_v2_model_fields(Model) is None


def test_try_get_v1_model_fields_handles_exception():
    class Raising:
        def __get__(self, obj, objtype=None):
            raise RuntimeError

    class Model:
        __fields__ = Raising()

    assert compat._try_get_v1_model_fields(Model) is None
