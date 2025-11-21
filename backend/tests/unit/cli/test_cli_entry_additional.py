"""Additional tests for the Forge CLI entry module."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge.cli import entry


@pytest.fixture(autouse=True)
def restore_sys_exit(monkeypatch):
    """Ensure sys.exit is restored between tests."""
    original_exit = entry.sys.exit
    yield
    monkeypatch.setattr(entry.sys, "exit", original_exit)


def test_normalize_arguments_inserts_cli(monkeypatch):
    """When no subcommand is supplied, CLI should be inserted."""
    monkeypatch.setattr(entry.sys, "argv", ["forge"])
    entry._normalize_arguments()
    assert entry.sys.argv == ["forge", "cli"]


def test_normalize_arguments_preserves_explicit_command(monkeypatch):
    """If a subcommand is already present, arguments should not be modified."""
    monkeypatch.setattr(entry.sys, "argv", ["forge", "serve", "--gpu"])
    entry._normalize_arguments()
    assert entry.sys.argv == ["forge", "serve", "--gpu"]


def test_handle_help_request_triggers_subparser(monkeypatch):
    """Help requests should resolve the CLI subparser then exit cleanly."""
    captured = {}

    def fake_get_subparser(parser, name):
        captured["args"] = (parser, name)

    monkeypatch.setattr(entry, "get_subparser", fake_get_subparser)
    monkeypatch.setattr(
        entry.sys, "exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code))
    )

    with pytest.raises(SystemExit) as exc:
        entry._handle_help_request(parser := object())

    assert exc.value.code == 0
    assert captured["args"] == (parser, "cli")


def test_handle_version_request_exits_when_requested(monkeypatch):
    """Version flag should exit early."""
    monkeypatch.setattr(
        entry.sys, "exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code))
    )
    with pytest.raises(SystemExit) as exc:
        entry._handle_version_request(SimpleNamespace(version=True))
    assert exc.value.code == 0


def test_handle_version_request_noop_without_flag():
    """Version handling should be a no-op if flag is absent or false."""
    entry._handle_version_request(SimpleNamespace(version=False))
    entry._handle_version_request(SimpleNamespace())


def test_execute_command_launches_gui(monkeypatch):
    """The serve command should launch the GUI server."""
    called = {}
    monkeypatch.setattr(
        entry, "launch_gui_server", lambda **kwargs: called.setdefault("launch", kwargs)
    )
    parser = SimpleNamespace(
        print_help=lambda: pytest.fail("print_help should not be called")
    )
    args = SimpleNamespace(command="serve", mount_cwd=True, gpu=False)

    entry._execute_command(args, parser)
    assert called["launch"] == {"mount_cwd": True, "gpu": False}


def test_execute_command_runs_cli(monkeypatch):
    """The cli command should invoke run_cli_command."""
    captured = {}
    monkeypatch.setattr(
        entry, "run_cli_command", lambda args: captured.setdefault("args", args)
    )
    parser = SimpleNamespace(
        print_help=lambda: pytest.fail("print_help should not be called")
    )
    args = SimpleNamespace(command="cli")

    entry._execute_command(args, parser)
    assert captured["args"] is args


def test_execute_command_handles_unknown_command(monkeypatch):
    """Unknown commands should print help and exit with status 1."""
    printed = {"called": False}

    def print_help():
        printed["called"] = True

    parser = SimpleNamespace(print_help=print_help)
    args = SimpleNamespace(command="unknown")

    monkeypatch.setattr(
        entry.sys, "exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code))
    )

    with pytest.raises(SystemExit) as exc:
        entry._execute_command(args, parser)

    assert exc.value.code == 1
    assert printed["called"] is True


def test_main_help_flow(monkeypatch):
    """Main should forward --help to the CLI subparser and exit."""
    monkeypatch.setattr(entry.sys, "argv", ["forge", "--help"])

    parser = SimpleNamespace(
        parse_args=lambda: SimpleNamespace(command="cli", version=False)
    )
    monkeypatch.setattr(entry, "get_cli_parser", lambda: parser)

    called = {}
    monkeypatch.setattr(
        entry,
        "get_subparser",
        lambda parser, name: called.setdefault("subparser", (parser, name)),
    )
    monkeypatch.setattr(
        entry.sys, "exit", lambda code=0: (_ for _ in ()).throw(SystemExit(code))
    )

    with pytest.raises(SystemExit) as exc:
        entry.main()

    assert exc.value.code == 0
    assert called["subparser"][1] == "cli"


def test_main_cli_flow(monkeypatch):
    """Main should normalize args, parse options and execute the cli command."""
    monkeypatch.setattr(entry.sys, "argv", ["forge", "cli"])

    parser_calls = []

    class DummyParser:
        def parse_args(self):
            parser_calls.append("parse_args")
            return SimpleNamespace(command="cli", version=False)

        def print_help(self):
            parser_calls.append("print_help")

    parser = DummyParser()
    monkeypatch.setattr(entry, "get_cli_parser", lambda: parser)

    executed = {}
    monkeypatch.setattr(
        entry, "run_cli_command", lambda args: executed.setdefault("args", args)
    )

    entry.main()

    assert parser_calls == ["parse_args"]
    assert executed["args"].command == "cli"


def test_main_serve_flow(monkeypatch):
    """Main should dispatch the serve command to the GUI launcher."""
    monkeypatch.setattr(entry.sys, "argv", ["forge", "serve"])

    class ServeParser:
        def parse_args(self):
            return SimpleNamespace(
                command="serve", mount_cwd=False, gpu=True, version=False
            )

        def print_help(self):
            pytest.fail("print_help should not be invoked")

    monkeypatch.setattr(entry, "get_cli_parser", ServeParser)

    launched = {}
    monkeypatch.setattr(
        entry,
        "launch_gui_server",
        lambda **kwargs: launched.setdefault("kwargs", kwargs),
    )

    entry.main()
    assert launched["kwargs"] == {"mount_cwd": False, "gpu": True}
