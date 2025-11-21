import base64
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, Callable, cast

import pytest
from pydantic import SecretStr

from forge.server.routes import analytics as analytics_routes
from forge.storage.conversation.conversation_store import ConversationStore
from forge.storage.files import FileStore


def _make_base64_json(data: dict) -> str:
    return base64.b64encode(json.dumps(data).encode("utf-8")).decode("utf-8")


class LambdaFileStore(FileStore):
    def __init__(self, reader: Callable[[str], str]):
        self._reader = reader

    def write(self, path: str, contents: str | bytes) -> None:
        raise NotImplementedError

    def read(self, path: str) -> str:
        return self._reader(path)

    def list(self, path: str) -> list[str]:
        return []

    def delete(self, path: str) -> None:
        raise NotImplementedError


class StubConversationStore(ConversationStore):
    def __init__(self, search_fn: Callable[[str | None, int], list[Any]]):
        self._search_fn = search_fn

    async def save_metadata(self, metadata):  # type: ignore[override]
        raise NotImplementedError

    async def get_metadata(self, conversation_id):  # type: ignore[override]
        raise NotImplementedError

    async def delete_metadata(self, conversation_id):  # type: ignore[override]
        raise NotImplementedError

    async def exists(self, conversation_id: str) -> bool:
        return False

    async def search(self, page_id: str | None = None, limit: int = 20):  # type: ignore[override]
        return SimpleNamespace(results=self._search_fn(page_id, limit))

    @classmethod
    async def get_instance(cls, config, user_id):  # type: ignore[override]
        raise NotImplementedError


def test_parse_period_variants():
    now = datetime.now()
    start_today, end_today = analytics_routes._parse_period("today")
    assert end_today >= start_today
    assert (now - start_today).days <= 1

    start_week, _ = analytics_routes._parse_period("week")
    assert (datetime.now() - start_week).days >= 6

    start_month, _ = analytics_routes._parse_period("month")
    assert (datetime.now() - start_month).days >= 29

    start_all, _ = analytics_routes._parse_period("all")
    assert start_all.year == 2020


def test_load_metrics_from_file_json(monkeypatch):
    file_store = LambdaFileStore(
        lambda filename: _make_base64_json({"service": {"cost": 1}})
    )
    data = analytics_routes._load_metrics_from_file(file_store, "file.json")
    assert data == {"service": {"cost": 1}}


def test_load_metrics_from_file_pickle(monkeypatch):
    import pickle

    pickled = base64.b64encode(pickle.dumps({"legacy": True})).decode("utf-8")

    file_store = LambdaFileStore(lambda filename: pickled)
    data = analytics_routes._load_metrics_from_file(file_store, "file.pickle")
    assert data == {"legacy": True}


def test_load_metrics_from_file_error(monkeypatch):
    def _raise(_filename: str) -> str:
        raise IOError("boom")

    file_store = LambdaFileStore(_raise)
    assert analytics_routes._load_metrics_from_file(file_store, "file") is None


def test_calculate_percentile():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert analytics_routes._calculate_percentile(values, 50) == 3
    assert analytics_routes._calculate_percentile(values, 99) == 5
    assert analytics_routes._calculate_percentile([], 50) == 0.0


@pytest.mark.asyncio
async def test_get_all_conversation_metrics_filters(monkeypatch):
    now = datetime.now()
    conv_in = SimpleNamespace(conversation_id="conv-in", created_at=now)
    conv_out = SimpleNamespace(
        conversation_id="conv-out", created_at=now - timedelta(days=10)
    )

    store = StubConversationStore(lambda _page_id, _limit: [conv_in, conv_out])
    data_map = {
        "file-conv-in": _make_base64_json({"svc": {"accumulated_cost": 2}}),
    }
    file_store = LambdaFileStore(
        lambda filename: data_map.get(filename, _make_base64_json({}))
    )

    monkeypatch.setattr(
        analytics_routes,
        "get_conversation_stats_filename",
        lambda conversation_id, user_id: f"file-{conversation_id}",
    )

    start, end = now - timedelta(days=1), now + timedelta(seconds=1)
    metrics, conversations = await analytics_routes._get_all_conversation_metrics(
        store,
        file_store,
        user_id="user",
        start_date=start,
        end_date=end,
    )

    assert conversations == [conv_in]
    assert metrics[0]["conversation_id"] == "conv-in"


@pytest.mark.asyncio
async def test_get_all_conversation_metrics_handles_exception(monkeypatch):
    def raise_search(_page_id: str | None, _limit: int) -> list[Any]:
        raise RuntimeError("fail")

    metrics, conversations = await analytics_routes._get_all_conversation_metrics(
        StubConversationStore(raise_search),
        LambdaFileStore(lambda _: _make_base64_json({})),
        user_id="user",
        start_date=datetime.now(),
        end_date=datetime.now(),
    )

    assert metrics == [] and conversations == []


@pytest.mark.asyncio
async def test_fetch_conversations(monkeypatch):
    store = StubConversationStore(lambda _page_id, _limit: [1, 2])
    conversations = await analytics_routes._fetch_conversations(store, "user")
    assert conversations == [1, 2]


def test_normalize_and_range_checks():
    start = datetime.now(timezone.utc)
    end = datetime.now()
    start_naive, end_naive = analytics_routes._normalize_date_range(start, end)
    assert start_naive.tzinfo is None and end_naive.tzinfo is None

    conv = SimpleNamespace(created_at=start_naive + timedelta(minutes=1))
    assert analytics_routes._is_in_date_range(conv, start_naive, end_naive)


def test_load_conversation_metrics(monkeypatch):
    monkeypatch.setattr(
        analytics_routes,
        "get_conversation_stats_filename",
        lambda conversation_id, user_id: "file-key",
    )

    file_store = LambdaFileStore(lambda _: _make_base64_json({"svc": {"token": 1}}))
    conv = SimpleNamespace(conversation_id="conv1")
    metrics = analytics_routes._load_conversation_metrics(conv, "user", file_store)
    assert metrics[0]["conversation_id"] == "conv1"


def test_aggregate_helpers():
    all_metrics = [
        {
            "token_usages": [
                {
                    "model": "gpt",
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "cache_read_tokens": 2,
                    "cache_write_tokens": 1,
                },
            ],
            "costs": [{"model": "gpt", "cost": 1.2}],
            "response_latencies": [{"latency": 0.3}],
        }
    ]

    total_tokens, total_requests, model_stats = analytics_routes._aggregate_token_usage(
        all_metrics
    )
    assert total_tokens == 15 and total_requests == 1
    assert model_stats["gpt"].cache_hit_tokens == 2

    costs = analytics_routes._aggregate_costs(all_metrics)
    assert costs["gpt"] == 1.2

    response_times = analytics_routes._aggregate_response_times(all_metrics)
    assert response_times == [0.3]

    metrics_tuple = analytics_routes._calculate_performance_metrics(response_times)
    assert metrics_tuple[0] == pytest.approx(0.3)


@pytest.mark.asyncio
async def test_get_analytics_dashboard_full(monkeypatch):
    conversations = [SimpleNamespace(conversation_id="conv", created_at=datetime.now())]

    conversation_store = StubConversationStore(lambda _page_id, _limit: conversations)

    file_store = LambdaFileStore(
        lambda _: _make_base64_json(
            {
                "svc": {
                    "accumulated_cost": 3,
                    "token_usages": [
                        {
                            "model": "gpt",
                            "prompt_tokens": 5,
                            "completion_tokens": 5,
                            "cache_read_tokens": 1,
                            "cache_write_tokens": 1,
                        }
                    ],
                    "costs": [{"model": "gpt", "cost": 3}],
                    "response_latencies": [{"latency": 0.5}],
                }
            }
        )
    )

    monkeypatch.setattr(analytics_routes, "file_store", file_store)
    monkeypatch.setattr(
        analytics_routes,
        "get_conversation_stats_filename",
        lambda conversation_id, user_id: "file-key",
    )

    result = await analytics_routes.get_analytics_dashboard(
        period="week",
        user_id="user",
        conversation_store=conversation_store,
    )

    assert result.summary.total_cost == 3
    assert result.models[0].model_name == "gpt"


@pytest.mark.asyncio
async def test_get_analytics_dashboard_no_store():
    result = await analytics_routes.get_analytics_dashboard(
        period="week",
        user_id="user",
        conversation_store=None,
    )
    assert result.summary.total_cost == 0


@pytest.mark.asyncio
async def test_get_analytics_dashboard_exception(monkeypatch):
    async def failing_get(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(analytics_routes, "_get_all_conversation_metrics", failing_get)

    result = await analytics_routes.get_analytics_dashboard(
        period="week",
        user_id="user",
        conversation_store=cast(ConversationStore, SimpleNamespace()),
    )
    assert result.summary.total_cost == 0


@pytest.mark.asyncio
async def test_get_analytics_summary_success(monkeypatch):
    conversations = [SimpleNamespace(conversation_id="conv", created_at=datetime.now())]

    conversation_store = StubConversationStore(lambda _page_id, _limit: conversations)

    metrics_payload = {
        "svc": {
            "accumulated_cost": 4,
            "token_usages": [
                {"model": "gpt", "prompt_tokens": 2, "completion_tokens": 2}
            ],
            "response_latencies": [{"latency": 0.2}],
            "costs": [{"model": "gpt", "cost": 4}],
        }
    }

    monkeypatch.setattr(
        analytics_routes,
        "file_store",
        LambdaFileStore(lambda _: _make_base64_json(metrics_payload)),
    )
    monkeypatch.setattr(
        analytics_routes, "get_conversation_stats_filename", lambda *_: "file-key"
    )

    summary = await analytics_routes.get_analytics_summary(
        period="week",
        user_id="user",
        conversation_store=conversation_store,
    )

    assert summary.total_cost == 4
    assert summary.total_requests == 1


@pytest.mark.asyncio
async def test_get_analytics_summary_no_store():
    summary = await analytics_routes.get_analytics_summary(
        period="week",
        user_id="user",
        conversation_store=None,
    )
    assert summary.total_cost == 0


@pytest.mark.asyncio
async def test_get_analytics_summary_exception(monkeypatch):
    async def failing_get(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(analytics_routes, "_get_all_conversation_metrics", failing_get)
    summary = await analytics_routes.get_analytics_summary(
        period="week",
        user_id="user",
        conversation_store=cast(ConversationStore, SimpleNamespace()),
    )
    assert summary.total_cost == 0


def test_calculate_totals_and_averages():
    totals = analytics_routes._calculate_totals(
        [
            {
                "accumulated_cost": 5,
                "token_usages": [{"prompt_tokens": 1, "completion_tokens": 1}],
                "response_latencies": [{"latency": 0.1}],
            }
        ]
    )
    assert totals["cost"] == 5

    averages = analytics_routes._calculate_averages(totals, 1)
    assert averages["cost"] == 5
    assert analytics_routes._calculate_averages(totals, 0)["cost"] == 0


@pytest.mark.asyncio
async def test_get_model_usage_success(monkeypatch):
    all_metrics = [
        {
            "token_usages": [
                {"model": "gpt", "prompt_tokens": 1, "completion_tokens": 1}
            ],
            "costs": [{"model": "gpt", "cost": 2}],
        }
    ]

    async def fake_get(*args, **kwargs):
        return all_metrics, []

    monkeypatch.setattr(analytics_routes, "_get_all_conversation_metrics", fake_get)
    stats = await analytics_routes.get_model_usage(
        "week", "user", cast(ConversationStore, SimpleNamespace())
    )
    assert stats[0].total_cost == 2


@pytest.mark.asyncio
async def test_get_model_usage_no_store():
    stats = await analytics_routes.get_model_usage("week", "user", None)
    assert stats == []


@pytest.mark.asyncio
async def test_get_model_usage_exception(monkeypatch):
    async def failing(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(analytics_routes, "_get_all_conversation_metrics", failing)
    stats = await analytics_routes.get_model_usage(
        "week", "user", cast(ConversationStore, SimpleNamespace())
    )
    assert stats == []


def test_aggregate_model_metrics_helpers():
    metrics = [
        {
            "token_usages": [
                {"model": "gpt", "prompt_tokens": 1, "completion_tokens": 2}
            ],
            "costs": [{"model": "gpt", "cost": 3}],
        }
    ]

    stats, costs = analytics_routes._aggregate_model_metrics(metrics)
    analytics_routes._apply_costs_to_stats(stats, costs)
    assert stats["gpt"].total_completion_tokens == 2
    assert stats["gpt"].total_cost == 3


@pytest.mark.asyncio
async def test_get_cost_breakdown_success(monkeypatch):
    all_metrics = [{"accumulated_cost": 1, "costs": [{"model": "gpt", "cost": 1}]}]

    async def fake_get(*args, **kwargs):
        return all_metrics, []

    monkeypatch.setattr(analytics_routes, "_get_all_conversation_metrics", fake_get)
    breakdown = await analytics_routes.get_cost_breakdown(
        "week", "user", cast(ConversationStore, SimpleNamespace())
    )
    assert breakdown.total_cost == 1
    assert breakdown.by_model["gpt"] == 1


@pytest.mark.asyncio
async def test_get_cost_breakdown_no_store():
    breakdown = await analytics_routes.get_cost_breakdown("week", "user", None)
    assert breakdown.total_cost == 0


@pytest.mark.asyncio
async def test_get_cost_breakdown_exception(monkeypatch):
    async def failing(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(analytics_routes, "_get_all_conversation_metrics", failing)
    breakdown = await analytics_routes.get_cost_breakdown(
        "week", "user", cast(ConversationStore, SimpleNamespace())
    )
    assert breakdown.total_cost == 0


def test_empty_dashboard():
    dashboard = analytics_routes._empty_dashboard("week", "now")
    assert dashboard.summary.total_cost == 0


def test_initialize_optimization_data():
    data = analytics_routes._initialize_optimization_data()
    assert data["enabled"] is False


def test_process_prompt_metrics(monkeypatch):
    registry = SimpleNamespace(
        get_all_variants=lambda prompt_id: ["base", "variant"],
    )
    tracker = SimpleNamespace(
        get_all_metrics=lambda prompt_id: {
            "base": SimpleNamespace(composite_score=0.1, avg_token_cost=2),
            "variant": SimpleNamespace(composite_score=0.5, avg_token_cost=1),
        }
    )
    optimized, variants, improvement, savings = (
        analytics_routes._process_prompt_metrics("prompt", registry, tracker)
    )
    assert optimized == 1
    assert variants == 2
    assert improvement == 0.5
    assert savings == 0.1


def test_process_prompt_metrics_no_registry():
    assert analytics_routes._process_prompt_metrics("prompt", None, None) == (
        0,
        0,
        0.0,
        0.0,
    )


def test_extract_optimization_data(monkeypatch):
    registry = SimpleNamespace(
        get_all_prompt_ids=lambda: ["p1"],
        get_all_variants=lambda prompt_id: ["base", "variant"],
    )
    tracker = SimpleNamespace(
        get_all_metrics=lambda prompt_id: {
            "base": SimpleNamespace(composite_score=0.2, avg_token_cost=5)
        }
    )
    session = SimpleNamespace(
        agent=SimpleNamespace(
            prompt_optimizer={
                "registry": registry,
                "tracker": tracker,
                "optimizer": object(),
            }
        ),
    )

    data = analytics_routes._extract_optimization_data(session)
    assert data is not None
    assert data["enabled"] is True
    assert data["total_prompts"] == 1


def test_extract_optimization_data_missing():
    assert analytics_routes._extract_optimization_data(SimpleNamespace()) is None


@pytest.mark.asyncio
async def test_get_prompt_optimization_analytics(monkeypatch):
    session = SimpleNamespace(agent=SimpleNamespace(prompt_optimizer=None))

    class FakeManager:
        def get_active_sessions(self):
            return [session]

    monkeypatch.setattr(analytics_routes, "SessionManager", lambda: FakeManager())

    data = await analytics_routes.get_prompt_optimization_analytics()
    assert "prompt_optimization" in data


@pytest.mark.asyncio
async def test_get_prompt_optimization_analytics_error(monkeypatch):
    def failing_manager():
        raise RuntimeError("boom")

    monkeypatch.setattr(analytics_routes, "SessionManager", failing_manager)
    data = await analytics_routes.get_prompt_optimization_analytics()
    assert data["prompt_optimization"]["enabled"] is False
    assert data["prompt_optimization"]["error"] == "boom"
