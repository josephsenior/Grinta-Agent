"""Additional unit tests for forge.cli.commands to improve coverage."""

from __future__ import annotations

import contextlib
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from forge.cli import commands
from forge.core.config import ForgeConfig
from forge.core.config.mcp_config import (
    MCPConfig,
    MCPSHTTPServerConfig,
    MCPSSEServerConfig,
    MCPStdioServerConfig,
)


class DummyConfig(SimpleNamespace):
    """Lightweight config with sandbox attribute for tests."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not hasattr(self, "sandbox"):
            self.sandbox = SimpleNamespace(trusted_dirs=[])


def make_config(**kwargs: Any) -> ForgeConfig:
    """Construct a flexible ForgeConfig-compatible object for tests."""
    return cast(ForgeConfig, DummyConfig(**kwargs))


@pytest.mark.asyncio
async def test_collect_input_handles_normal_input(monkeypatch):
    """collect_input should trim whitespace and return user input."""
    outputs = []
    monkeypatch.setattr(
        commands,
        "print_formatted_text",
        lambda message="", end="\n": outputs.append((message, end)),
    )

    async def fake_prompt(config, prompt, *, multiline):
        assert prompt == ""
        assert multiline is False
        return "  hello world  "

    monkeypatch.setattr(commands, "read_prompt_input", fake_prompt)
    result = await commands.collect_input(make_config(), "Prompt:")
    assert result == "hello world"
    assert outputs[-1][0] == "Prompt:"


@pytest.mark.asyncio
async def test_collect_input_handles_cancel(monkeypatch):
    """collect_input should return None when user cancels."""
    monkeypatch.setattr(commands, "print_formatted_text", lambda *args, **kwargs: None)

    async def fake_prompt(*args, **kwargs):
        return "/exit"

    monkeypatch.setattr(commands, "read_prompt_input", fake_prompt)

    result = await commands.collect_input(make_config(), "Prompt:")
    assert result is None


def test_restart_cli_success(monkeypatch):
    """restart_cli should call os.execv with the running interpreter."""
    called: dict[str, tuple[str, tuple[str, ...]]] = {}
    monkeypatch.setattr(commands, "print_formatted_text", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        commands.os,
        "execv",
        lambda exe, argv: called.setdefault("args", (exe, tuple(argv))),
    )

    commands.restart_cli()

    assert called["args"][0] == commands.sys.executable
    assert called["args"][1][0] == commands.sys.executable


def test_restart_cli_failure(monkeypatch):
    """Exceptions from os.execv should be reported to the user."""
    messages = []
    monkeypatch.setattr(
        commands,
        "print_formatted_text",
        lambda message, **kwargs: messages.append(message),
    )

    def raise_execv(*_, **__):
        raise OSError("boom")

    monkeypatch.setattr(commands.os, "execv", raise_execv)
    commands.restart_cli()
    assert any("Failed to restart CLI" in msg for msg in messages)
    assert any("Please restart Forge manually" in msg for msg in messages)


@pytest.mark.asyncio
async def test_prompt_for_restart(monkeypatch):
    """prompt_for_restart should loop until it receives a valid answer."""
    responses = iter(["maybe", " y ", "ignored"])

    class DummySession:
        async def prompt_async(self, *args, **kwargs):
            return next(responses)

    monkeypatch.setattr(
        commands, "create_prompt_session", lambda config: DummySession()
    )
    monkeypatch.setattr(commands, "patch_stdout", lambda: contextlib.nullcontext())
    monkeypatch.setattr(commands, "print_formatted_text", lambda *args, **kwargs: None)

    result = await commands.prompt_for_restart(make_config())
    assert result is True


@pytest.mark.asyncio
async def test_prompt_for_restart_negative(monkeypatch):
    """prompt_for_restart should return False when user declines."""
    responses = iter(["  no  "])

    class DummySession:
        async def prompt_async(self, *args, **kwargs):
            return next(responses)

    monkeypatch.setattr(
        commands, "create_prompt_session", lambda config: DummySession()
    )
    monkeypatch.setattr(commands, "patch_stdout", lambda: contextlib.nullcontext())
    monkeypatch.setattr(commands, "print_formatted_text", lambda *args, **kwargs: None)

    result = await commands.prompt_for_restart(make_config())
    assert result is False


def test_parse_replay_command_valid(monkeypatch):
    """_parse_replay_command should parse manifest path and assert flag."""
    outputs = []
    monkeypatch.setattr(
        commands, "print_formatted_text", lambda message: outputs.append(message)
    )

    parsed = commands._parse_replay_command("/replay path/to/manifest --assert")
    assert parsed == ("path/to/manifest", True)
    assert outputs == []


def test_parse_replay_command_missing_path(monkeypatch):
    """_parse_replay_command should print usage when arguments are missing."""
    outputs = []
    monkeypatch.setattr(
        commands, "print_formatted_text", lambda message: outputs.append(message)
    )
    assert commands._parse_replay_command("/replay") is None
    assert "Usage" in outputs[0]


def test_display_replay_helpers(monkeypatch):
    """Replay display helpers should format the summary and diffs."""
    outputs = []
    monkeypatch.setattr(
        commands, "print_formatted_text", lambda message: outputs.append(message)
    )

    result = {
        "ok": False,
        "summary": {"steps": 3, "diff_count": 2},
        "diffs": ["diff1", "diff2"],
    }
    commands._display_replay_result(result, "manifest.json", assert_mode=True)
    assert any("Replay DIFFS" in message for message in outputs)
    assert any("diff1" in message for message in outputs)
    assert any("Assertion failed" in message for message in outputs)


@pytest.mark.asyncio
async def test_handle_replay_command_success(monkeypatch):
    """_handle_replay_command should call replay_manifest and display results."""
    monkeypatch.setattr(
        commands, "_parse_replay_command", lambda command: ("manifest.json", False)
    )
    monkeypatch.setattr(
        commands,
        "replay_manifest",
        lambda path, assert_mode=False: {
            "ok": True,
            "summary": {"steps": 1, "diff_count": 0},
            "diffs": [],
        },
    )

    called: dict[str, tuple[dict[str, object], str, bool]] = {}
    monkeypatch.setattr(
        commands,
        "_display_replay_result",
        lambda result, path, assert_mode: called.setdefault(
            "args", (result, path, assert_mode)
        ),
    )

    await commands._handle_replay_command("/replay manifest.json")
    assert called["args"][1] == "manifest.json"


@pytest.mark.asyncio
async def test_handle_replay_command_error(monkeypatch):
    """Replay errors should be reported without raising."""
    from forge.metasop.replay import ReplayError

    monkeypatch.setattr(
        commands, "_parse_replay_command", lambda command: ("manifest.json", False)
    )
    monkeypatch.setattr(
        commands,
        "replay_manifest",
        lambda *args, **kwargs: (_ for _ in ()).throw(ReplayError("err")),
    )

    outputs = []
    monkeypatch.setattr(
        commands, "print_formatted_text", lambda message: outputs.append(message)
    )

    await commands._handle_replay_command("/replay manifest.json")
    assert any("Replay error" in msg for msg in outputs)


@pytest.mark.asyncio
async def test_handle_capaudit_command_json(monkeypatch):
    """Capability audit command should support JSON output."""
    monkeypatch.setattr(commands, "load_role_profiles", lambda: ["profile"])
    monkeypatch.setattr(
        commands, "audit_capabilities", lambda profiles, sops_dir: {"profiles_count": 1}
    )

    outputs = []
    monkeypatch.setattr(
        commands, "print_formatted_text", lambda message: outputs.append(message)
    )

    await commands._handle_capaudit_command("/capaudit --json")
    assert outputs
    assert '{\n  "profiles_count": 1\n}' in outputs[0]


@pytest.mark.asyncio
async def test_handle_capaudit_command_summary(monkeypatch):
    """Capability audit summary should list key sections."""
    report = {
        "profiles_count": 2,
        "sops_scanned": 4,
        "unknown_capabilities": ["foo"],
        "unused_capabilities": [],
        "steps_missing_capabilities": [
            {"sop": "A", "step_id": "1", "role": "dev", "missing": ["x"]}
        ],
        "capability_usage": {"cap1": 3, "cap2": 1},
    }
    monkeypatch.setattr(commands, "load_role_profiles", lambda: ["profile"])
    monkeypatch.setattr(
        commands, "audit_capabilities", lambda profiles, sops_dir: report
    )

    outputs = []
    monkeypatch.setattr(
        commands, "print_formatted_text", lambda message: outputs.append(message)
    )

    await commands._handle_capaudit_command("/capaudit")
    assert any("Capability Audit Summary" in msg for msg in outputs)
    assert any("Unknown capabilities" in msg for msg in outputs)


@pytest.mark.asyncio
async def test_init_repository_existing_file(monkeypatch, tmp_path):
    """init_repository should display existing repo instructions and allow re-init."""
    repo_dir = tmp_path / ".Forge" / "microagents"
    repo_dir.mkdir(parents=True)
    repo_file = repo_dir / "repo.md"
    repo_file.write_text("Existing instructions", encoding="utf-8")

    monkeypatch.setattr(commands, "Frame", lambda *args, **kwargs: None)
    monkeypatch.setattr(commands, "TextArea", lambda *args, **kwargs: None)
    monkeypatch.setattr(commands, "print_container", lambda *args, **kwargs: None)
    monkeypatch.setattr(commands, "print_formatted_text", lambda *args, **kwargs: None)
    monkeypatch.setattr(commands, "cli_confirm", lambda *args, **kwargs: 0)

    cleared: dict[str, Path] = {}
    monkeypatch.setattr(
        commands,
        "write_to_file",
        lambda path, content: cleared.setdefault("path", path),
    )

    result = await commands.init_repository(make_config(), str(tmp_path))
    assert result is True
    assert cleared["path"] == repo_file


@pytest.mark.asyncio
async def test_init_repository_new_file(monkeypatch, tmp_path):
    """init_repository should prompt to create repo.md when missing."""
    monkeypatch.setattr(commands, "print_formatted_text", lambda *args, **kwargs: None)
    monkeypatch.setattr(commands, "cli_confirm", lambda *args, **kwargs: 1)
    result = await commands.init_repository(make_config(), str(tmp_path))
    assert result is False


def test_check_folder_security_agreement_trusted(monkeypatch):
    """If folder is already trusted, the agreement should pass silently."""
    config = make_config()
    config.sandbox.trusted_dirs = ["/path"]
    monkeypatch.setattr(commands, "get_local_config_trusted_dirs", lambda: ["/path"])
    assert commands.check_folder_security_agreement(config, "/path") is True


def test_check_folder_security_agreement_prompt(monkeypatch):
    """When folder is untrusted, user confirmation should add it to local config."""
    config = make_config()
    config.sandbox.trusted_dirs = []
    monkeypatch.setattr(commands, "get_local_config_trusted_dirs", lambda: [])
    monkeypatch.setattr(commands, "clear", lambda: None)
    monkeypatch.setattr(commands, "print_container", lambda *args, **kwargs: None)
    monkeypatch.setattr(commands, "print_formatted_text", lambda *args, **kwargs: None)
    monkeypatch.setattr(commands, "cli_confirm", lambda *args, **kwargs: 0)

    added: dict[str, str] = {}
    monkeypatch.setattr(
        commands,
        "add_local_config_trusted_dir",
        lambda path: added.setdefault("path", path),
    )

    assert commands.check_folder_security_agreement(config, "/new") is True
    assert added["path"] == "/new"


def test_get_config_file_path_prefers_current_dir(monkeypatch, tmp_path):
    """Config path should prefer ./config.toml if present."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(commands.Path, "cwd", lambda: tmp_path)
    monkeypatch.setattr(commands.Path, "home", lambda: Path("/home/user"))
    assert commands.get_config_file_path() == config_file


def test_get_config_file_path_defaults_to_home(monkeypatch, tmp_path):
    """If config.toml missing locally, fallback to ~/.Forge/config.toml."""
    monkeypatch.setattr(commands.Path, "cwd", lambda: tmp_path)
    monkeypatch.setattr(commands.Path, "home", lambda: Path("/home/user"))
    expected = Path("/home/user/.Forge/config.toml")
    assert commands.get_config_file_path() == expected


def test_load_config_file_existing(monkeypatch, tmp_path):
    """load_config_file should parse TOML when available."""
    file_path = tmp_path / "config.toml"
    file_path.write_text('title = "config"', encoding="utf-8")
    assert commands.load_config_file(file_path)["title"] == "config"


def test_load_config_file_missing(monkeypatch, tmp_path):
    """Missing config files should return empty dict after creating directories."""
    file_path = tmp_path / "nested" / "config.toml"
    data = commands.load_config_file(file_path)
    assert data == {}
    assert file_path.parent.exists()


def test_save_config_file_writes_arrays(tmp_path):
    """save_config_file should serialize MCP sections using arrays."""
    config_data = {
        "mcp": {
            "stdio_servers": [{"name": "test", "command": "uvx"}],
        },
        "other": {"enabled": True},
    }
    file_path = tmp_path / "config.toml"
    commands.save_config_file(config_data, file_path)
    contents = file_path.read_text(encoding="utf-8")
    assert 'stdio_servers = [{name = "test", command = "uvx"}]' in contents
    assert "other" in contents


def test_ensure_mcp_config_structure():
    """_ensure_mcp_config_structure should create the mcp entry if missing."""
    config: dict[str, object] = {}
    commands._ensure_mcp_config_structure(config)
    assert "mcp" in config
    commands._ensure_mcp_config_structure(config)
    assert config["mcp"] == {}


def test_add_server_to_config(tmp_path, monkeypatch):
    """_add_server_to_config should append to the designated server list."""
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr(commands, "get_config_file_path", lambda: config_path)
    monkeypatch.setattr(commands, "load_config_file", lambda path: {})
    saved: dict[str, dict[str, object]] = {}
    monkeypatch.setattr(
        commands, "save_config_file", lambda data, path: saved.setdefault("data", data)
    )

    returned_path = commands._add_server_to_config("stdio_servers", {"name": "test"})
    assert returned_path == config_path
    saved_data = saved["data"]
    mcp_section = cast(dict[str, object], saved_data["mcp"])
    stdio_servers = cast(list[dict[str, object]], mcp_section["stdio_servers"])
    assert stdio_servers[0]["name"] == "test"


@pytest.mark.asyncio
async def test_add_mcp_server_dispatch(monkeypatch):
    """add_mcp_server should dispatch to the correct transport helper."""
    config = make_config()
    calls = []
    monkeypatch.setattr(commands, "cli_confirm", lambda *args, **kwargs: 0)
    monkeypatch.setattr(commands, "add_sse_server", lambda cfg: calls.append("sse"))
    await commands.add_mcp_server(config)
    assert calls == ["sse"]


@pytest.mark.asyncio
async def test_add_mcp_server_cancel(monkeypatch):
    """Selecting cancel should stop without action."""
    config = make_config()
    monkeypatch.setattr(commands, "cli_confirm", lambda *args, **kwargs: 3)
    await commands.add_mcp_server(config)


@pytest.mark.asyncio
async def test_collect_sse_server_inputs(monkeypatch):
    """_collect_sse_server_inputs should gather URL and optional API key."""
    responses = iter(["https://example.com", ""])

    async def fake_collect(*args, **kwargs):
        return next(responses)

    monkeypatch.setattr(commands, "collect_input", fake_collect)
    url, api_key = await commands._collect_sse_server_inputs(make_config())
    assert url == "https://example.com"
    assert api_key is None


@pytest.mark.asyncio
async def test_collect_sse_server_inputs_cancel(monkeypatch):
    """Canceling during SSE input should return sentinel values."""

    async def fake_collect(*args, **kwargs):
        return None

    monkeypatch.setattr(commands, "collect_input", fake_collect)
    assert await commands._collect_sse_server_inputs(make_config()) == (None, None)


@pytest.mark.asyncio
async def test_add_sse_server_success(monkeypatch, tmp_path):
    """add_sse_server should persist the server configuration and optionally restart."""
    responses = iter(["https://example.com", "secret"])

    async def fake_collect(config):
        return next(responses), next(responses)

    monkeypatch.setattr(commands, "_collect_sse_server_inputs", fake_collect)

    async def fake_validate(config, url, api_key):
        return MCPSSEServerConfig(url=url, api_key=api_key)

    monkeypatch.setattr(commands, "_validate_and_create_sse_server", fake_validate)
    monkeypatch.setattr(
        commands,
        "_add_server_to_config",
        lambda server_type, config_dict: tmp_path / f"{server_type}.toml",
    )

    async def prompt_no_restart(config):
        return False

    monkeypatch.setattr(commands, "prompt_for_restart", prompt_no_restart)
    monkeypatch.setattr(commands, "restart_cli", lambda: None)
    monkeypatch.setattr(commands, "print_formatted_text", lambda *args, **kwargs: None)

    await commands.add_sse_server(make_config())


@pytest.mark.asyncio
async def test_add_sse_server_cancel(monkeypatch):
    """Cancellation during SSE collection should abort the operation."""

    async def fake_collect(config):
        return None, None

    monkeypatch.setattr(commands, "_collect_sse_server_inputs", fake_collect)
    outputs = []
    monkeypatch.setattr(
        commands, "print_formatted_text", lambda message: outputs.append(message)
    )
    await commands.add_sse_server(make_config())
    assert any("Operation cancelled" in msg for msg in outputs)


@pytest.mark.asyncio
async def test_collect_stdio_server_inputs(monkeypatch):
    """_collect_stdio_server_inputs should gather required details."""
    responses = iter(["tool", "uvx", "--flag", "ENV=1"])

    async def fake_collect(*args, **kwargs):
        return next(responses)

    monkeypatch.setattr(commands, "collect_input", fake_collect)
    assert await commands._collect_stdio_server_inputs(make_config()) == (
        "tool",
        "uvx",
        "--flag",
        "ENV=1",
    )


@pytest.mark.asyncio
async def test_add_stdio_server_success(monkeypatch, tmp_path):
    """add_stdio_server should validate inputs and save the configuration."""
    responses = iter([("tool", "uvx", "--flag", "ENV=1")])

    async def fake_collect(config):
        return next(responses)

    monkeypatch.setattr(commands, "_collect_stdio_server_inputs", fake_collect)

    async def fake_name_check(config, name):
        return True

    async def fake_validate_inputs(config, name, command, args, env):
        return MCPStdioServerConfig(name=name, command=command, args=args, env=env)

    monkeypatch.setattr(commands, "_validate_stdio_server_name", fake_name_check)
    monkeypatch.setattr(commands, "_validate_stdio_server_inputs", fake_validate_inputs)
    monkeypatch.setattr(
        commands,
        "_add_server_to_config",
        lambda server_type, config_dict: tmp_path / f"{server_type}.toml",
    )

    async def prompt_no_restart(config):
        return False

    monkeypatch.setattr(commands, "prompt_for_restart", prompt_no_restart)
    monkeypatch.setattr(commands, "print_formatted_text", lambda *args, **kwargs: None)

    await commands.add_stdio_server(make_config())


@pytest.mark.asyncio
async def test_add_stdio_server_name_conflict(monkeypatch):
    """Duplicate stdio server names should trigger retry flow."""
    responses = iter([("tool", "uvx", "", ""), ("tool", "uvx", "", "")])

    async def fake_collect(config):
        return next(responses)

    monkeypatch.setattr(commands, "_collect_stdio_server_inputs", fake_collect)

    async def fake_name_check(config, name):
        return False

    monkeypatch.setattr(commands, "_validate_stdio_server_name", fake_name_check)
    monkeypatch.setattr(commands, "cli_confirm", lambda *args, **kwargs: 1)
    outputs = []
    monkeypatch.setattr(
        commands, "print_formatted_text", lambda message: outputs.append(message)
    )
    await commands.add_stdio_server(make_config())
    assert any("Operation cancelled" in msg for msg in outputs)


@pytest.mark.asyncio
async def test_collect_shttp_server_inputs(monkeypatch):
    """_collect_shttp_server_inputs should request URL and optional key."""
    responses = iter(["https://example.com", "apikey"])

    async def fake_collect(*args, **kwargs):
        return next(responses)

    monkeypatch.setattr(commands, "collect_input", fake_collect)
    assert await commands._collect_shttp_server_inputs(make_config()) == (
        "https://example.com",
        "apikey",
    )


@pytest.mark.asyncio
async def test_add_shttp_server(monkeypatch, tmp_path):
    """add_shttp_server should create config entry and respect restart prompt."""
    responses = iter([("https://example.com", None)])

    async def fake_collect(config):
        return next(responses)

    monkeypatch.setattr(commands, "_collect_shttp_server_inputs", fake_collect)

    async def fake_validate(config, url, api_key):
        return MCPSHTTPServerConfig(url=url, api_key=api_key)

    monkeypatch.setattr(commands, "_validate_and_create_shttp_server", fake_validate)
    monkeypatch.setattr(
        commands,
        "_add_server_to_config",
        lambda server_type, config_dict: tmp_path / f"{server_type}.toml",
    )

    async def prompt_restart(config):
        return True

    monkeypatch.setattr(commands, "prompt_for_restart", prompt_restart)
    restarted: dict[str, bool] = {}
    monkeypatch.setattr(
        commands, "restart_cli", lambda: restarted.setdefault("called", True)
    )
    monkeypatch.setattr(commands, "print_formatted_text", lambda *args, **kwargs: None)

    await commands.add_shttp_server(make_config())
    assert restarted["called"] is True


def test_collect_available_servers():
    """_collect_available_servers should flatten MCP config lists."""
    config = MCPConfig(
        sse_servers=[MCPSSEServerConfig(url="http://a")],
        stdio_servers=[MCPStdioServerConfig(name="stdio", command="uvx")],
        shttp_servers=[MCPSHTTPServerConfig(url="http://b")],
    )
    servers = commands._collect_available_servers(config)
    assert ("SSE", "http://a", config.sse_servers[0]) in servers
    assert ("Stdio", "stdio", config.stdio_servers[0]) in servers
    assert ("SHTTP", "http://b", config.shttp_servers[0]) in servers


def test_remove_server_helpers():
    """Removal helper functions should mutate config dictionaries appropriately."""
    config_data = {
        "mcp": {
            "sse_servers": [{"url": "http://a"}],
            "stdio_servers": [{"name": "stdio"}],
            "shttp_servers": [{"url": "http://b"}],
        }
    }
    assert commands._remove_sse_server(config_data, "http://a") is True
    assert commands._remove_stdio_server(config_data, "stdio") is True
    assert commands._remove_shttp_server(config_data, "http://b") is True


@pytest.mark.asyncio
async def test_remove_mcp_server(monkeypatch, tmp_path):
    """remove_mcp_server should remove a selected server and persist config."""
    config = make_config(
        mcp=MCPConfig(stdio_servers=[MCPStdioServerConfig(name="stdio", command="uvx")])
    )
    selections = iter([0, 0])  # select stdio server, confirm removal
    monkeypatch.setattr(
        commands, "cli_confirm", lambda *args, **kwargs: next(selections)
    )
    monkeypatch.setattr(
        commands, "get_config_file_path", lambda: tmp_path / "config.toml"
    )
    monkeypatch.setattr(
        commands,
        "load_config_file",
        lambda path: {"mcp": {"stdio_servers": [{"name": "stdio"}]}},
    )
    saved: dict[str, dict[str, object]] = {}
    monkeypatch.setattr(
        commands, "save_config_file", lambda data, path: saved.setdefault("data", data)
    )

    async def prompt_no_restart(config):
        return False

    monkeypatch.setattr(commands, "prompt_for_restart", prompt_no_restart)
    monkeypatch.setattr(commands, "print_formatted_text", lambda *args, **kwargs: None)

    await commands.remove_mcp_server(config)
    saved_data = saved["data"]
    mcp_section = cast(dict[str, object], saved_data["mcp"])
    stdio_servers = cast(list[dict[str, object]], mcp_section["stdio_servers"])
    assert stdio_servers == []
