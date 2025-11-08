import json
from forge.core.pydantic_compat import model_dump_json, model_dump_with_options, model_to_dict


class V2Like:

    def __init__(self, data):
        self._data = data

    def model_dump(self, **kwargs):
        if kwargs.get("exclude_none"):
            return {k: v for k, v in self._data.items() if v is not None}
        return dict(self._data)

    def model_dump_json(self, **kwargs):
        return json.dumps(self.model_dump(**kwargs))


class V1Like:

    def __init__(self, data):
        self._data = data

    def dict(self, **kwargs):
        if kwargs.get("exclude_none"):
            return {k: v for k, v in self._data.items() if v is not None}
        return dict(self._data)

    def json(self, **kwargs):
        return json.dumps(self.dict(**kwargs))


def test_model_dump_with_options_v2_like():
    obj = V2Like({"a": 1, "b": None})
    assert model_dump_with_options(obj) == {"a": 1, "b": None}
    assert model_dump_with_options(obj, exclude_none=True) == {"a": 1}


def test_model_dump_with_options_v1_like():
    obj = V1Like({"x": 2, "y": None})
    assert model_dump_with_options(obj) == {"x": 2, "y": None}
    assert model_dump_with_options(obj, exclude_none=True) == {"x": 2}


def test_model_dump_json_v2_like():
    obj = V2Like({"a": 1, "b": 2})
    s = model_dump_json(obj)
    assert isinstance(s, str)
    assert json.loads(s) == {"a": 1, "b": 2}


def test_model_dump_json_v1_like():
    obj = V1Like({"m": 9, "n": None})
    s = model_dump_json(obj)
    assert isinstance(s, str)
    assert json.loads(s) == {"m": 9, "n": None}


def test_model_to_dict_passthrough_dict():
    d = {"z": 5}
    assert model_to_dict(d) == {"z": 5}


def test_model_dump_with_options_mode_json_falls_back_to_json_method():

    class V1JSON:

        def __init__(self, d):
            self._d = d

        def json(self, **kwargs):
            return json.dumps(self._d)

    v = V1JSON({"k": "v"})
    s = model_dump_with_options(v, mode="json")
    assert s == {"k": "v"}
