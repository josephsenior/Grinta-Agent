"""Tests for public options routes."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge.server.routes import public as public_routes


@pytest.mark.asyncio
async def test_get_litellm_models(monkeypatch):
    monkeypatch.setattr(
        public_routes,
        "get_supported_llm_models",
        lambda cfg: ["gpt-4", "gpt-3.5-turbo"],
    )
    assert await public_routes.get_litellm_models() == ["gpt-4", "gpt-3.5-turbo"]


@pytest.mark.asyncio
async def test_get_agents(monkeypatch):
    monkeypatch.setattr(
        public_routes.Agent, "list_agents", lambda: ["beta", "alpha", "gamma"]
    )
    assert await public_routes.get_agents() == ["alpha", "beta", "gamma"]


@pytest.mark.asyncio
async def test_get_security_analyzers(monkeypatch):
    monkeypatch.setattr(
        public_routes, "SecurityAnalyzers", {"bandit": object(), "semgrep": object()}
    )
    assert await public_routes.get_security_analyzers() == ["bandit", "semgrep"]


@pytest.mark.asyncio
async def test_get_config(monkeypatch):
    fake_config = {"app_mode": "TEST", "feature_flags": {"x": True}}
    monkeypatch.setattr(public_routes.server_config, "get_config", lambda: fake_config)
    assert await public_routes.get_config() == fake_config
