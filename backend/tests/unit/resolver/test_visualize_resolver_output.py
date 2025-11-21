import json
import pytest


def test_structured_dump_uses_print_json(monkeypatch, capsys):
    fake_resolver = object()
    fake_obj = {"a": 1}
    monkeypatch.setattr(
        "forge.resolver.visualize_resolver_output.load_single_resolver_output",
        lambda path, num: fake_resolver,
    )
    monkeypatch.setattr(
        "forge.resolver.visualize_resolver_output.model_dump_with_options",
        lambda x: fake_obj,
    )
    called = {}

    def fake_print_json_stdout(obj, pretty=False):
        called["obj"] = obj
        called["pretty"] = pretty

    monkeypatch.setattr(
        "forge.resolver.visualize_resolver_output.print_json_stdout",
        fake_print_json_stdout,
    )
    from forge.resolver.visualize_resolver_output import visualize_resolver_output

    visualize_resolver_output(issue_number=1, output_dir="/tmp", vis_method="json")  # nosec B108 - Safe: test call
    assert called.get("obj") == fake_obj
    assert called.get("pretty") is True


def test_fallback_to_model_dump_json(monkeypatch, capsys):
    fake_resolver = object()
    json_str = json.dumps({"x": 2})
    monkeypatch.setattr(
        "forge.resolver.visualize_resolver_output.load_single_resolver_output",
        lambda path, num: fake_resolver,
    )
    monkeypatch.setattr(
        "forge.resolver.visualize_resolver_output.model_dump_with_options",
        lambda x: iter(()).throw(RuntimeError("nope")),
    )
    monkeypatch.setattr(
        "forge.resolver.visualize_resolver_output.model_dump_json", lambda x: json_str
    )
    called = {}

    def fake_print_json_stdout(obj, pretty=False):
        called["obj"] = obj
        called["pretty"] = pretty

    monkeypatch.setattr(
        "forge.resolver.visualize_resolver_output.print_json_stdout",
        fake_print_json_stdout,
    )
    from forge.resolver.visualize_resolver_output import visualize_resolver_output

    visualize_resolver_output(issue_number=1, output_dir="/tmp", vis_method="json")  # nosec B108 - Safe: test call
    assert called.get("obj") == {"x": 2}
    assert called.get("pretty") is True


def test_no_dump_fallback_prints_repr(monkeypatch, capsys):
    fake_resolver = object()
    monkeypatch.setattr(
        "forge.resolver.visualize_resolver_output.load_single_resolver_output",
        lambda path, num: fake_resolver,
    )
    monkeypatch.setattr(
        "forge.resolver.visualize_resolver_output.model_dump_with_options", None
    )
    monkeypatch.setattr(
        "forge.resolver.visualize_resolver_output.model_dump_json", None
    )
    monkeypatch.setattr(
        "forge.resolver.visualize_resolver_output.print_json_stdout", None
    )
    from forge.resolver.visualize_resolver_output import visualize_resolver_output

    visualize_resolver_output(issue_number=1, output_dir="/tmp", vis_method="json")  # nosec B108 - Safe: test call
    captured = capsys.readouterr()
    assert captured.out.strip().startswith(
        "<object"
    ) or captured.out.strip().startswith("object")


def test_invalid_vis_method_raises(monkeypatch):
    monkeypatch.setattr(
        "forge.resolver.visualize_resolver_output.load_single_resolver_output",
        lambda path, num: object(),
    )
    from forge.resolver.visualize_resolver_output import visualize_resolver_output

    with pytest.raises(ValueError):
        visualize_resolver_output(issue_number=1, output_dir="/tmp", vis_method="xml")  # nosec B108 - Safe: test call
