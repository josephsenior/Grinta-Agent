from types import SimpleNamespace

from forge.core import message_utils


def _make_event(event_id, response_id=None, tool_id=None):
    tool_metadata = None
    if tool_id is not None:
        tool_metadata = SimpleNamespace(model_response={"id": tool_id})
    return SimpleNamespace(
        id=event_id, response_id=response_id, tool_call_metadata=tool_metadata
    )


def _make_metrics(usages):
    return SimpleNamespace(
        token_usages=[SimpleNamespace(response_id=u) for u in usages]
    )


def test_get_token_usage_for_event_none_args():
    metrics = _make_metrics(["resp-1"])
    assert message_utils.get_token_usage_for_event(None, metrics) is None
    assert message_utils.get_token_usage_for_event(_make_event(1), None) is None


def test_get_token_usage_for_event_matches_tool_response():
    event = _make_event(1, tool_id="resp-2")
    metrics = _make_metrics(["resp-2", "resp-3"])
    usage = message_utils.get_token_usage_for_event(event, metrics)
    assert usage is not None
    assert usage.response_id == "resp-2"


def test_get_token_usage_for_event_fallback_response_id():
    event = _make_event(1, response_id="resp-4")
    metrics = _make_metrics(["resp-4"])
    usage = message_utils.get_token_usage_for_event(event, metrics)
    assert usage is not None
    assert usage.response_id == "resp-4"


def test_get_token_usage_for_event_id_not_found():
    events = [
        _make_event(1, response_id="resp-1"),
        _make_event(2, response_id="resp-2"),
    ]
    metrics = _make_metrics(["resp-1", "resp-2"])
    assert message_utils.get_token_usage_for_event_id(events, 99, metrics) is None


def test_get_token_usage_for_event_id_backtracks():
    events = [
        _make_event(1, response_id="resp-1"),
        _make_event(2, response_id="resp-2"),
        _make_event(3, response_id=None, tool_id="resp-3"),
    ]
    metrics = _make_metrics(["resp-3", "resp-2", "resp-1"])
    usage = message_utils.get_token_usage_for_event_id(events, 3, metrics)
    assert usage is not None
    assert usage.response_id == "resp-3"


def test_get_token_usage_for_event_no_match():
    event = _make_event(1, response_id="resp-missing")
    metrics = _make_metrics(["resp-1"])
    assert message_utils.get_token_usage_for_event(event, metrics) is None


def test_get_token_usage_for_event_id_backtrack_none():
    events = [
        _make_event(1, response_id="resp-1"),
        _make_event(2, response_id="resp-2"),
    ]
    metrics = _make_metrics(["other"])
    assert message_utils.get_token_usage_for_event_id(events, 2, metrics) is None
