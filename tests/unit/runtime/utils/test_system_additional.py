from __future__ import annotations

import importlib.util
import os
import random
import sys
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[4] / "forge" / "runtime" / "utils" / "system.py"
SPEC = importlib.util.spec_from_file_location("forge.runtime.utils.system", ROOT)
assert SPEC and SPEC.loader
system_mod = importlib.util.module_from_spec(SPEC)
sys.modules["forge.runtime.utils.system"] = system_mod
SPEC.loader.exec_module(system_mod)

check_port_available = system_mod.check_port_available
find_available_tcp_port = system_mod.find_available_tcp_port
display_number_matrix = system_mod.display_number_matrix


def test_check_port_available_true(monkeypatch):
    sockets = []

    class DummySocket:
        def __init__(self, *args, **kwargs):
            sockets.append(self)
            self.bound = False
            self.closed = False

        def bind(self, address):
            self.bound = True

        def close(self):
            self.closed = True

    monkeypatch.setattr(
        system_mod.socket,
        "socket",
        lambda *args, **kwargs: DummySocket(),
        raising=False,
    )
    assert check_port_available(12345) is True
    assert sockets[0].bound is True
    assert sockets[0].closed is True


def test_check_port_available_false(monkeypatch):
    sockets = []

    class DummySocket:
        def __init__(self):
            sockets.append(self)
            self.closed = False

        def bind(self, address):
            raise OSError("in use")

        def close(self):
            self.closed = True

    monkeypatch.setattr(
        system_mod.socket,
        "socket",
        lambda *args, **kwargs: DummySocket(),
        raising=False,
    )
    monkeypatch.setattr(
        system_mod.time, "sleep", lambda *args, **kwargs: None, raising=False
    )
    assert check_port_available(23456) is False
    assert sockets[0].closed is True


def test_find_available_tcp_port(monkeypatch):
    calls = []
    ports_sequence = [30001, 30002, 30003]

    def fake_shuffle(seq):
        # keep order to make deterministic
        pass

    def fake_check(port):
        calls.append(port)
        return port == 30002

    class DummyRandom:
        def shuffle(self, seq):
            fake_shuffle(seq)

    monkeypatch.setattr(
        system_mod.random, "SystemRandom", lambda: DummyRandom(), raising=False
    )
    monkeypatch.setattr(system_mod, "check_port_available", fake_check, raising=False)
    result = find_available_tcp_port(min_port=30001, max_port=30003, max_attempts=3)
    assert result == 30002
    assert calls == [30001, 30002]


def test_find_available_tcp_port_returns_negative(monkeypatch):
    def fake_check(port):
        return False

    monkeypatch.setattr(system_mod, "check_port_available", fake_check, raising=False)
    monkeypatch.setattr(
        system_mod.random, "SystemRandom", lambda: random.Random(0), raising=False
    )
    result = find_available_tcp_port(min_port=40000, max_port=40001, max_attempts=2)
    assert result == -1


@pytest.mark.parametrize(
    ("number", "expected_first_line"),
    [
        (0, "###"),
        (10, "  # ###"),
        (98, "### ###"),
    ],
)
def test_display_number_matrix(number, expected_first_line):
    matrix = display_number_matrix(number)
    assert matrix is not None
    lines = matrix.strip("\n").splitlines()
    assert lines[0] == expected_first_line


def test_display_number_matrix_out_of_range():
    assert display_number_matrix(-1) is None
    assert display_number_matrix(1000) is None
