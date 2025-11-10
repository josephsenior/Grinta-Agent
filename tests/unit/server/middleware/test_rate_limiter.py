"""Tests for rate limiting middleware."""

from __future__ import annotations

import os
import time
from types import SimpleNamespace

import pytest

from starlette.requests import Request
from starlette.responses import Response

from forge.server.middleware import rate_limiter as rate_module
from forge.server.middleware.rate_limiter import (
    EndpointRateLimiter,
    RateLimiter,
    RedisRateLimiter,
    _rate_limit_store,
)


def _make_request(
    path: str = "/api/run",
    method: str = "POST",
    headers: dict[str, str] | None = None,
    client_host: str = "1.1.1.1",
) -> Request:
    headers = headers or {}
    raw_headers = [(k.encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()]
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": raw_headers,
        "client": (client_host, 12345),
        "server": ("localhost", 8000),
        "scheme": "http",
    }
    request = Request(scope)
    request.state.user_id = "user-123"
    return request


@pytest.fixture(autouse=True)
def clear_rate_store():
    _rate_limit_store.clear()
    yield
    _rate_limit_store.clear()


@pytest.mark.asyncio
async def test_rate_limiter_allows_within_limits():
    limiter = RateLimiter(requests_per_hour=5, burst_limit=3)

    async def call_next(request):  # pylint: disable=unused-argument
        return Response(content="ok", media_type="application/json")

    request = _make_request()
    response = await limiter(request, call_next)
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "5"
    assert response.headers["X-RateLimit-Remaining"] == "4"


@pytest.mark.asyncio
async def test_rate_limiter_disabled():
    limiter = RateLimiter(enabled=False)

    async def call_next(request):
        return Response(content="ok")

    response = await limiter(_make_request(), call_next)
    assert "X-RateLimit-Limit" not in response.headers


@pytest.mark.asyncio
async def test_rate_limiter_skips_health_and_assets():
    limiter = RateLimiter()

    async def call_next(request):
        return Response(content="ok")

    for path in ["/health", "/", "/assets/logo.png"]:
        response = await limiter(_make_request(path=path, method="GET"), call_next)
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limiter_hourly_limit_exceeded():
    limiter = RateLimiter(requests_per_hour=2, burst_limit=2)
    key = "user:user-123"
    _rate_limit_store[key] = [time.time() - 1, time.time() - 2]

    async def call_next(request):
        pytest.fail("call_next should not be invoked when rate limited")

    response = await limiter(_make_request(), call_next)
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"


@pytest.mark.asyncio
async def test_rate_limiter_burst_limit_exceeded():
    limiter = RateLimiter(requests_per_hour=100, burst_limit=1)
    key = "user:user-123"
    _rate_limit_store[key] = [time.time() - 10]

    async def call_next(request):
        pytest.fail("call_next should not be invoked when burst limit exceeded")

    response = await limiter(_make_request(), call_next)
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_rate_limiter_get_key_fallback_ip():
    limiter = RateLimiter()
    request = _make_request()
    del request.state.user_id
    key = await limiter._get_rate_limit_key(request)
    assert key.startswith("ip:")

    forwarded_request = _make_request(headers={"x-forwarded-for": "2.3.4.5"})
    del forwarded_request.state.user_id
    forwarded_key = await limiter._get_rate_limit_key(forwarded_request)
    assert forwarded_key == "ip:2.3.4.5"


@pytest.mark.asyncio
async def test_rate_limiter_remaining_requests():
    limiter = RateLimiter(requests_per_hour=5)
    key = "user:user-remaining"
    now = time.time()
    _rate_limit_store[key] = [now - 100, now - 200, now - 4000]  # only two within hour

    remaining = await limiter._get_remaining_requests(key)
    assert remaining == 3


@pytest.mark.asyncio
async def test_endpoint_rate_limiter_uses_env(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "42")
    monkeypatch.setenv("RATE_LIMIT_BURST", "7")
    limiter = EndpointRateLimiter()

    async def call_next(request):
        return Response(content="ok")

    request = _make_request(path="/api/conversations/list")
    response = await limiter(request, call_next)
    assert response.headers["X-RateLimit-Limit"] == "42"
    assert response.headers["X-RateLimit-Remaining"] == "41"


def test_endpoint_rate_limiter_default_limit(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_REQUESTS", raising=False)
    monkeypatch.delenv("RATE_LIMIT_BURST", raising=False)
    limiter = EndpointRateLimiter()
    limits = limiter._get_limits_for_path("/api/unknown/path")
    assert limits == limiter.LIMITS["default"]


@pytest.mark.asyncio
async def test_endpoint_rate_limiter_disabled():
    limiter = EndpointRateLimiter(enabled=False)

    async def call_next(request):
        return Response(content="ok")

    response = await limiter(_make_request(path="/api/prompts"), call_next)
    assert "X-RateLimit-Limit" not in response.headers


class DummyRedis:
    def __init__(self):
        self.data = {}
        self.last_expire = None

    async def ping(self):
        pass

    async def zremrangebyscore(self, key, start, end):  # pylint: disable=unused-argument
        self.data.setdefault(key, [])
        self.data[key] = [score for score in self.data[key] if score[1] > end]

    async def zcount(self, key, start, end):
        self.data.setdefault(key, [])
        return sum(1 for score in self.data[key] if start <= score[1] <= end)

    async def zadd(self, key, mapping):
        self.data.setdefault(key, [])
        for member, score in mapping.items():
            self.data[key].append((member, score))

    async def expire(self, key, ttl):
        self.last_expire = (key, ttl)


@pytest.fixture
def patch_redis(monkeypatch):
    dummy = DummyRedis()
    monkeypatch.setattr(rate_module, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(rate_module, "redis", SimpleNamespace(from_url=lambda *args, **kwargs: dummy))
    return dummy


@pytest.mark.asyncio
async def test_redis_rate_limiter_success(patch_redis):
    limiter = RedisRateLimiter(enabled=True)

    async def call_next(request):
        return Response(content="ok")

    response = await limiter(_make_request(), call_next)
    assert response.status_code == 200
    redis_key = f"ratelimit:user:user-123"
    assert patch_redis.data[redis_key]  # request was recorded


@pytest.mark.asyncio
async def test_redis_rate_limiter_exceeds_hour(monkeypatch, patch_redis):
    limiter = RedisRateLimiter(requests_per_hour=1, burst_limit=10)

    async def call_next(request):
        return Response(content="ok")

    request = _make_request()
    await limiter(request, call_next)
    response = await limiter(request, call_next)
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_redis_rate_limiter_handles_error(monkeypatch):
    limiter = RedisRateLimiter()

    class FailingRedis:
        async def ping(self):
            pass

        async def zremrangebyscore(self, *args, **kwargs):
            raise RuntimeError("fail")

    monkeypatch.setattr(rate_module, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(rate_module, "redis", SimpleNamespace(from_url=lambda *args, **kwargs: FailingRedis()))

    async def call_next(request):
        return Response(content="ok")

    response = await limiter(_make_request(), call_next)
    assert response.status_code == 200  # fail-open


@pytest.mark.asyncio
async def test_redis_rate_limiter_get_remaining(monkeypatch, patch_redis):
    limiter = RedisRateLimiter(requests_per_hour=5)
    key = "ratelimit:user:user-123"
    now = int(time.time())
    patch_redis.data[key] = [("member", now - 10), ("member2", now - 20)]

    remaining = await limiter._get_remaining_requests("user:user-123")
    assert remaining == 3


@pytest.mark.asyncio
async def test_redis_rate_limiter_fallback_remaining(monkeypatch):
    monkeypatch.setattr(rate_module, "REDIS_AVAILABLE", False)
    limiter = RedisRateLimiter(requests_per_hour=5)
    _rate_limit_store["user:fallback"] = [time.time()]
    remaining = await limiter._get_remaining_requests("user:fallback")
    assert remaining == 4


@pytest.mark.asyncio
async def test_redis_rate_limiter_connection_failure(monkeypatch, caplog):
    limiter = RedisRateLimiter()
    caplog.set_level("WARNING")

    class FailingRedis:
        async def ping(self):
            raise RuntimeError("no redis")

    monkeypatch.setattr(rate_module, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(rate_module, "redis", SimpleNamespace(from_url=lambda *args, **kwargs: FailingRedis()))

    client = await limiter._get_redis_client()
    assert client is None


@pytest.mark.asyncio
async def test_redis_rate_limiter_fallback_to_super(monkeypatch):
    monkeypatch.setattr(rate_module, "REDIS_AVAILABLE", False)
    limiter = RedisRateLimiter(requests_per_hour=2, burst_limit=1)
    key = "user:fallback"
    _rate_limit_store[key] = [time.time() - 120]
    result = await limiter._check_rate_limit(key)
    assert result is True


@pytest.mark.asyncio
async def test_redis_rate_limiter_burst_limit(monkeypatch):
    limiter = RedisRateLimiter(requests_per_hour=10, burst_limit=1)

    class BurstRedis:
        async def ping(self):
            pass

        async def zremrangebyscore(self, *args, **kwargs):
            pass

        async def zcount(self, key, start, end):  # pylint: disable=unused-argument
            # First call (hour window) should return 0, second call (burst window) returns 1
            if not hasattr(self, "called"):
                self.called = True
                return 0
            return 1

        async def zadd(self, *args, **kwargs):
            pytest.fail("zadd should not be called when burst limit exceeded")

        async def expire(self, *args, **kwargs):
            pass

    monkeypatch.setattr(rate_module, "REDIS_AVAILABLE", True)
    monkeypatch.setattr(rate_module, "redis", SimpleNamespace(from_url=lambda *args, **kwargs: BurstRedis()))

    async def call_next(request):
        return Response(content="ok")

    response = await limiter(_make_request(), call_next)
    assert response.status_code == 429
