"""Unit tests for SessionManager."""

from __future__ import annotations

from types import SimpleNamespace

from forge.server.session.session_manager import SessionManager


def make_session(session_id: str, **attributes):
    attrs = {"sid": session_id}
    attrs.update(attributes)
    return SimpleNamespace(**attrs)


def test_session_manager_add_and_get_session():
    manager = SessionManager()
    session = make_session("session-1", user_id="user-1")
    manager.add_session(session)

    retrieved = manager.get_session("session-1")
    assert retrieved is session
    assert manager.get_session_count() == 1


def test_session_manager_get_active_sessions_returns_copy():
    manager = SessionManager()
    session = make_session("session-1")
    manager.add_session(session)

    active = manager.get_active_sessions()
    assert active == {"session-1": session}
    active["session-1"] = None
    assert manager.get_session("session-1") is session  # original unaffected


def test_session_manager_remove_session():
    manager = SessionManager()
    manager.add_session(make_session("session-1"))
    manager.add_session(make_session("session-2"))

    manager.remove_session("session-1")
    assert manager.get_session("session-1") is None
    assert manager.get_session_count() == 1


def test_session_manager_remove_missing_does_not_error():
    manager = SessionManager()
    manager.add_session(make_session("session-1"))
    manager.remove_session("missing")
    assert manager.get_session_count() == 1
