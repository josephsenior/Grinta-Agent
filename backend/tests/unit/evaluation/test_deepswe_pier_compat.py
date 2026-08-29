from pathlib import Path

from evaluation.deepswe.pier_compat import normalize_shell_script_lf


def test_normalize_shell_script_lf_rewrites_crlf(tmp_path: Path) -> None:
    script = tmp_path / 'start-squid.sh'
    script.write_bytes(b'#!/bin/sh\r\necho ready\r\n')

    assert normalize_shell_script_lf(script) is True
    assert script.read_bytes() == b'#!/bin/sh\necho ready\n'
    assert normalize_shell_script_lf(script) is False
