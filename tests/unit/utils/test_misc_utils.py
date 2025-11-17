from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace

import pytest

from forge.utils import http_session
from forge.utils import import_utils
from forge.utils import metrics_labels
from forge.utils import search_utils
from forge.utils import tenacity_metrics


def test_sanitize_operation_label() -> None:
    assert metrics_labels.sanitize_operation_label("My Operation") == "My_Operation"
    assert metrics_labels.sanitize_operation_label("123value").startswith("op_")
    assert metrics_labels.sanitize_operation_label("") == "unknown"
    assert metrics_labels.sanitize_operation_label(123) == "op_123"


def test_import_utils(monkeypatch: pytest.MonkeyPatch) -> None:
    class Base:
        pass

    class Impl(Base):
        pass

    modules = {
        "pkg.module": SimpleNamespace(),
        "pkg.module.submodule": SimpleNamespace(answer=99),
        "pkg.impl": SimpleNamespace(Impl=Impl),
    }

    monkeypatch.setattr(
        import_utils.importlib, "import_module", lambda name: modules[name]
    )

    result = import_utils.import_from("pkg.module.submodule.answer")
    assert result == 99

    assert import_utils.get_impl(Base, "pkg.impl.Impl") is Impl
    assert import_utils.get_impl(Base, None) is Base


def test_http_session_merges_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {}

    class FakeClient:
        def request(self, method, url, **kwargs):
            called["method"] = method
            called["headers"] = kwargs["headers"]
            return "response"

        def stream(self, method, url, **kwargs):
            called["method"] = method
            called["headers"] = kwargs["headers"]
            return "stream"

    monkeypatch.setattr(http_session, "CLIENT", FakeClient())
    session = http_session.HttpSession(headers={"a": "1"})
    assert session.get("url", headers={"b": "2"}) == "response"
    assert called["headers"] == {"a": "1", "b": "2"}
    session.close()
    assert session.post("url") == "response"  # ensures reuse warning path resets flag
    session.close()
    assert session.stream("GET", "url") == "stream"


def test_search_utils_pagination():
    page_id = search_utils.offset_to_page_id(5, has_next=True)
    assert search_utils.page_id_to_offset(page_id) == 5
    assert search_utils.offset_to_page_id(0, has_next=False) is None


@pytest.mark.asyncio
async def test_search_utils_iterate():
    async def provider(page_id=None):
        if page_id is None:
            return SimpleNamespace(results=[1, 2], next_page_id="Mg==")  # base64 for 2
        return SimpleNamespace(results=[3], next_page_id=None)

    items = []
    async for item in search_utils.iterate(provider):
        items.append(item)
    assert items == [1, 2, 3]


def test_tenacity_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    events = []

    monkeypatch.setattr(
        tenacity_metrics, "_record_metrics_event_runtime", lambda ev: events.append(ev)
    )
    before = tenacity_metrics.tenacity_before_sleep_factory("My Op")
    after = tenacity_metrics.tenacity_after_factory("My Op")

    retry_state = SimpleNamespace(
        attempt_number=1, stop=SimpleNamespace(max_attempts=2)
    )
    before(retry_state)
    assert events[0]["status"] == "attempt"
    before(SimpleNamespace(attempt_number=2))

    outcome = SimpleNamespace(successful=lambda: True)
    retry_state = SimpleNamespace(outcome=outcome)
    after(retry_state)
    assert any(ev["status"] == "retry_success" for ev in events)

    events.clear()
    retry_state = SimpleNamespace(
        outcome=None,
        exception=RuntimeError("bad"),
        attempt_number=2,
        stop=SimpleNamespace(max_attempts=2),
    )
    after(retry_state)
    assert events[0]["status"] == "retry_failure"

    # call_tenacity_hooks should suppress errors from hooks
    def bad_hook(state):
        raise RuntimeError("boom")

    tenacity_metrics.call_tenacity_hooks(bad_hook, bad_hook, SimpleNamespace())

    class BoolError:
        def __bool__(self):
            raise ValueError("bool error")

    tenacity_metrics.call_tenacity_hooks(BoolError(), None, SimpleNamespace())

    class OutcomeError:
        def successful(self):
            raise RuntimeError("boom")

    events.clear()
    retry_state = SimpleNamespace(outcome=OutcomeError(), attempt_number=0, stop=None)
    after(retry_state)


def test_record_metrics_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyModule:
        @staticmethod
        def record_event(ev):
            raise RuntimeError("fail")

    monkeypatch.setitem(sys.modules, "forge.metasop.metrics", DummyModule)
    tenacity_metrics._record_metrics_event_runtime({"status": "attempt"})
