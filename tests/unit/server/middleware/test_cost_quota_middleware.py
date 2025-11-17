"""Tests for cost quota middleware behavior."""

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pytest

from starlette.requests import Request
from starlette.responses import Response

from forge.server.middleware.cost_quota import (
    CostQuotaMiddleware,
    QuotaPlan,
    QUOTA_CONFIGS,
    RedisCostQuotaMiddleware,
    _cost_store,
    get_cost_quota_middleware,
    record_llm_cost,
    _GLOBAL_QUOTA_MIDDLEWARE,
)


def _make_request(
    path: str = "/api/run",
    method: str = "POST",
    headers: dict[str, str] | None = None,
    client_host: str = "test-host",
) -> Request:
    headers_list = []
    headers = headers or {}
    for key, value in headers.items():
        headers_list.append((key.encode("latin-1"), value.encode("latin-1")))

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers_list,
        "client": (client_host, 123),
        "server": ("test", 80),
        "scheme": "http",
    }
    request = Request(scope)
    request.state.user_id = "user-1"
    request.state.quota_plan = "pro"
    return request


@pytest.fixture(autouse=True)
def clear_cost_store():
    _cost_store.clear()
    yield
    _cost_store.clear()


@pytest.mark.asyncio
async def test_cost_quota_middleware_allows_within_limits():
    middleware = CostQuotaMiddleware()

    async def call_next(request):  # pylint: disable=unused-argument
        return Response(content="ok")

    request = _make_request()
    response = await middleware(request, call_next)
    assert response.status_code == 200
    assert response.headers["X-Cost-Quota-Plan"] == "pro"


@pytest.mark.asyncio
async def test_cost_quota_middleware_skips_when_disabled():
    middleware = CostQuotaMiddleware(enabled=False)

    async def call_next(request):  # pylint: disable=unused-argument
        return Response(content="ok")

    request = _make_request()
    response = await middleware(request, call_next)
    assert response.status_code == 200
    assert "X-Cost-Quota-Plan" not in response.headers


@pytest.mark.asyncio
async def test_cost_quota_middleware_skips_health_assets():
    middleware = CostQuotaMiddleware()

    async def call_next(request):  # pylint: disable=unused-argument
        return Response(content="ok")

    request = _make_request("/health", method="GET")
    response = await middleware(request, call_next)
    assert response.status_code == 200

    request_assets = _make_request("/assets/js/app.js", method="GET")
    response_assets = await middleware(request_assets, call_next)
    assert response_assets.status_code == 200


@pytest.mark.asyncio
async def test_cost_quota_middleware_blocks_exceeded(monkeypatch):
    middleware = CostQuotaMiddleware()
    key = "user:user-1"
    config = QUOTA_CONFIGS[QuotaPlan.PRO]
    _cost_store[key]["daily_cost"] = config.daily_limit

    async def call_next(request):
        pytest.fail("call_next should not be invoked when quota exceeded")

    request = _make_request()
    response = await middleware(request, call_next)
    assert response.status_code == 429
    assert response.headers["X-Cost-Quota-Plan"] == "pro"
    import json

    body = json.loads(response.body)
    assert body["limit_type"] == "daily"


@pytest.mark.asyncio
async def test_get_quota_key_prefers_user(monkeypatch):
    middleware = CostQuotaMiddleware()
    request = _make_request()
    key = await middleware._get_quota_key(request)
    assert key == "user:user-1"

    request_no_user = _make_request(client_host="1.2.3.4")
    del request_no_user.state.user_id
    key_ip = await middleware._get_quota_key(request_no_user)
    assert key_ip == "ip:1.2.3.4"

    request_forwarded = _make_request(headers={"x-forwarded-for": "5.6.7.8"})
    del request_forwarded.state.user_id
    key_forwarded = await middleware._get_quota_key(request_forwarded)
    assert key_forwarded == "ip:5.6.7.8"


@pytest.mark.asyncio
async def test_get_user_plan_default_and_invalid():
    middleware = CostQuotaMiddleware(default_plan=QuotaPlan.PRO)
    request = _make_request()
    plan = await middleware._get_user_plan(request)
    assert plan == QuotaPlan.PRO

    request_invalid = _make_request()
    request_invalid.state.quota_plan = "not-a-plan"
    plan_default = await middleware._get_user_plan(request_invalid)
    assert plan_default == QuotaPlan.PRO


@pytest.mark.asyncio
async def test_check_quota_resets(monkeypatch):
    middleware = CostQuotaMiddleware()
    key = "user:user-reset"
    config = QUOTA_CONFIGS[QuotaPlan.FREE]
    data = _cost_store[key]
    data["daily_cost"] = config.daily_limit - 0.1
    data["monthly_cost"] = config.monthly_limit - 0.1
    data["last_reset_day"] = time.time() - middleware.day_window - 10
    data["last_reset_month"] = time.time() - middleware.month_window - 10

    within = await middleware._check_quota(key, QuotaPlan.FREE)
    assert within is True
    assert data["daily_cost"] == 0.0
    assert data["monthly_cost"] == 0.0


@pytest.mark.asyncio
async def test_quota_exceeded_response_monthly(monkeypatch):
    middleware = CostQuotaMiddleware()
    key = "user:user-month"
    config = QUOTA_CONFIGS[QuotaPlan.FREE]
    data = _cost_store[key]
    data["daily_cost"] = config.daily_limit - 0.1
    data["monthly_cost"] = config.monthly_limit + 1

    response = await middleware._quota_exceeded_response(key, QuotaPlan.FREE)
    assert response.status_code == 429
    import json

    body = json.loads(response.body)
    assert body["limit_type"] == "monthly"
    assert "Retry-After" in response.headers


@pytest.mark.asyncio
async def test_record_cost_updates_store(caplog):
    middleware = CostQuotaMiddleware()
    caplog.set_level("DEBUG")
    middleware.record_cost("user:user-1", 0.25)
    data = _cost_store["user:user-1"]
    assert data["daily_cost"] == pytest.approx(0.25)
    assert data["monthly_cost"] == pytest.approx(0.25)


def test_record_cost_disabled():
    middleware = CostQuotaMiddleware(enabled=False)
    middleware.record_cost("user:disabled", 1.0)
    assert _cost_store["user:disabled"]["daily_cost"] == 0


def test_global_getter_and_record_llm_cost(monkeypatch):
    from forge.server.middleware import cost_quota as module

    module._GLOBAL_QUOTA_MIDDLEWARE = None
    middleware = get_cost_quota_middleware()
    assert isinstance(middleware, CostQuotaMiddleware)
    record_llm_cost("user:global", 0.5)
    assert _cost_store["user:global"]["daily_cost"] == pytest.approx(0.5)
    module._GLOBAL_QUOTA_MIDDLEWARE = None


@pytest.mark.asyncio
async def test_redis_middleware_fallback(monkeypatch):
    middleware = RedisCostQuotaMiddleware(enabled=True, default_plan=QuotaPlan.FREE)

    class DummyRedis:
        def __init__(self):
            self.should_fail = False

        async def ping(self):
            pass

        async def get(self, key):  # pylint: disable=unused-argument
            return None

    monkeypatch.setattr(
        "forge.server.middleware.cost_quota.redis",
        SimpleNamespace(from_url=lambda *args, **kwargs: DummyRedis()),
    )
    monkeypatch.setattr("forge.server.middleware.cost_quota.REDIS_AVAILABLE", True)

    request = _make_request()
    await middleware._check_quota("user:user-redis", QuotaPlan.FREE)


@pytest.mark.asyncio
async def test_redis_middleware_allows_on_error(monkeypatch, caplog):
    middleware = RedisCostQuotaMiddleware(enabled=True)
    caplog.set_level("ERROR")

    class DummyRedis:
        async def ping(self):
            pass

        async def get(self, key):  # pylint: disable=unused-argument
            raise RuntimeError("redis down")

    monkeypatch.setattr(
        "forge.server.middleware.cost_quota.redis",
        SimpleNamespace(from_url=lambda *args, **kwargs: DummyRedis()),
    )
    monkeypatch.setattr("forge.server.middleware.cost_quota.REDIS_AVAILABLE", True)

    allowed = await middleware._check_quota("user:user-redis", QuotaPlan.FREE)
    assert allowed is True


@pytest.mark.asyncio
async def test_redis_middleware_respects_limits(monkeypatch):
    middleware = RedisCostQuotaMiddleware(enabled=True)

    class DummyRedis:
        async def ping(self):
            pass

        async def get(self, key):
            if "daily" in key:
                return 0
            if "monthly" in key:
                return QUOTA_CONFIGS[QuotaPlan.FREE].monthly_limit
            return 0

    dummy = DummyRedis()
    monkeypatch.setattr(
        "forge.server.middleware.cost_quota.redis",
        SimpleNamespace(from_url=lambda *args, **kwargs: dummy),
    )
    monkeypatch.setattr("forge.server.middleware.cost_quota.REDIS_AVAILABLE", True)

    allowed = await middleware._check_quota("user:limit", QuotaPlan.FREE)
    assert allowed is False


@pytest.mark.asyncio
async def test_redis_record_cost_async(monkeypatch, caplog):
    middleware = RedisCostQuotaMiddleware(enabled=True)
    caplog.set_level("DEBUG")

    class DummyRedis:
        async def ping(self):
            pass

        async def get(self, key):
            return None

        async def incrbyfloat(self, key, value):
            self.last_key = key
            self.last_value = value

        async def expire(self, key, ttl):
            self.last_expire = (key, ttl)

    dummy = DummyRedis()
    monkeypatch.setattr(
        "forge.server.middleware.cost_quota.redis",
        SimpleNamespace(from_url=lambda *args, **kwargs: dummy),
    )
    monkeypatch.setattr("forge.server.middleware.cost_quota.REDIS_AVAILABLE", True)

    await middleware.record_cost_async("user:user-redis", 1.5)
    assert dummy.last_value == 1.5
    assert dummy.last_expire[1] in {middleware.day_window, middleware.month_window}


@pytest.mark.asyncio
async def test_redis_record_cost_async_fallback(monkeypatch):
    middleware = RedisCostQuotaMiddleware(enabled=True)
    monkeypatch.setattr("forge.server.middleware.cost_quota.REDIS_AVAILABLE", False)

    await middleware.record_cost_async("user:none", 0.75)
    assert _cost_store["user:none"]["daily_cost"] == pytest.approx(0.75)


@pytest.mark.asyncio
async def test_redis_record_cost_async_handles_error(monkeypatch, caplog):
    middleware = RedisCostQuotaMiddleware(enabled=True)
    caplog.set_level("ERROR")

    class DummyRedis:
        async def ping(self):
            pass

        async def get(self, key):
            return None

        async def incrbyfloat(self, key, value):
            raise RuntimeError("incr failed")

        async def expire(self, key, ttl):
            pass

    dummy = DummyRedis()
    monkeypatch.setattr(
        "forge.server.middleware.cost_quota.redis",
        SimpleNamespace(from_url=lambda *args, **kwargs: dummy),
    )
    monkeypatch.setattr("forge.server.middleware.cost_quota.REDIS_AVAILABLE", True)

    await middleware.record_cost_async("user:error", 2.0)
    assert _cost_store["user:error"]["daily_cost"] == pytest.approx(2.0)


def test_redis_record_cost_disabled():
    middleware = RedisCostQuotaMiddleware(enabled=False)
    middleware.record_cost("user:skip", 5.0)
    assert _cost_store["user:skip"]["daily_cost"] == 0


def test_redis_record_cost_enabled():
    middleware = RedisCostQuotaMiddleware(enabled=True)
    middleware.record_cost("user:sync", 0.3)
    assert _cost_store["user:sync"]["daily_cost"] == pytest.approx(0.3)


@pytest.mark.asyncio
async def test_redis_record_cost_async_disabled():
    middleware = RedisCostQuotaMiddleware(enabled=False)
    await middleware.record_cost_async("user:skip", 5.0)
    assert _cost_store["user:skip"]["daily_cost"] == 0


@pytest.mark.asyncio
async def test_redis_connect_failure(monkeypatch, caplog):
    middleware = RedisCostQuotaMiddleware(enabled=True)
    caplog.set_level("WARNING")

    class FailingRedis:
        async def ping(self):
            raise RuntimeError("connect fail")

    monkeypatch.setattr(
        "forge.server.middleware.cost_quota.redis",
        SimpleNamespace(from_url=lambda *args, **kwargs: FailingRedis()),
    )
    monkeypatch.setattr("forge.server.middleware.cost_quota.REDIS_AVAILABLE", True)

    client = await middleware._get_redis_client()
    assert client is None


@pytest.mark.asyncio
async def test_redis_check_quota_fallback(monkeypatch):
    middleware = RedisCostQuotaMiddleware(enabled=True)
    monkeypatch.setattr("forge.server.middleware.cost_quota.REDIS_AVAILABLE", False)
    assert await middleware._check_quota("user:fallback", QuotaPlan.FREE) is True


@pytest.mark.asyncio
async def test_check_quota_monthly_limit(monkeypatch):
    middleware = CostQuotaMiddleware()
    key = "user:user-monthly-limit"
    data = _cost_store[key]
    data["daily_cost"] = 0
    data["monthly_cost"] = QUOTA_CONFIGS[QuotaPlan.FREE].monthly_limit
    assert await middleware._check_quota(key, QuotaPlan.FREE) is False


@pytest.mark.asyncio
async def test_redis_daily_limit(monkeypatch):
    middleware = RedisCostQuotaMiddleware(enabled=True)

    class DummyRedis:
        async def ping(self):
            pass

        async def get(self, key):
            if "daily" in key:
                return QUOTA_CONFIGS[QuotaPlan.FREE].daily_limit
            return 0

    dummy = DummyRedis()
    monkeypatch.setattr(
        "forge.server.middleware.cost_quota.redis",
        SimpleNamespace(from_url=lambda *args, **kwargs: dummy),
    )
    monkeypatch.setattr("forge.server.middleware.cost_quota.REDIS_AVAILABLE", True)

    allowed = await middleware._check_quota("user:daily", QuotaPlan.FREE)
    assert allowed is False
