from pathlib import Path

from evaluation.deepswe.pier_compat import (
    normalize_shell_script_lf,
    resilient_uv_tool_install,
)


def test_normalize_shell_script_lf_rewrites_crlf(tmp_path: Path) -> None:
    script = tmp_path / 'start-squid.sh'
    script.write_bytes(b'#!/bin/sh\r\necho ready\r\n')

    assert normalize_shell_script_lf(script) is True
    assert script.read_bytes() == b'#!/bin/sh\necho ready\n'
    assert normalize_shell_script_lf(script) is False


def test_resilient_uv_tool_install_retries_slow_downloads_in_one_layer() -> None:
    command = resilient_uv_tool_install(
        "git+https://example.invalid/Grinta Agent.git@abc'def"
    )

    assert 'UV_HTTP_TIMEOUT=300' in command
    assert 'UV_HTTP_RETRIES=10' in command
    assert 'for grinta_install_attempt in 1 2 3' in command
    assert 'sleep $((grinta_install_attempt * 10))' in command
    assert '--retry-all-errors' in command
    assert "'\"'\"'" in command
