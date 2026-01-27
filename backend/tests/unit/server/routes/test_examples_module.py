"""Tests for OpenAPI examples module."""

from __future__ import annotations

from typing import Any, Mapping, cast

from forge.server.routes import examples as examples_module


def test_settings_examples_structure():
    settings = cast(Mapping[str, Any], examples_module.SETTINGS_EXAMPLES)
    assert "basic_settings" in settings
    basic = settings["basic_settings"]
    assert basic["value"]["llm"]["model"].startswith("anthropic/")
    advanced = settings["advanced_settings"]
    assert advanced["value"]["security"]["confirmation_mode"] is True


def test_conversation_examples_variants():
    examples = cast(Mapping[str, Any], examples_module.CONVERSATION_EXAMPLES)
    assert {"simple_conversation", "with_repository"} <= set(
        examples
    )
    assert "github_repo" in examples["with_repository"]["value"]


def test_file_upload_examples():
    uploads = cast(Mapping[str, Any], examples_module.FILE_UPLOAD_EXAMPLES)
    single = uploads["single_file"]["value"]
    assert single["content"].startswith("flask==")
    multiple = uploads["multiple_files"]["value"]["files"]
    assert len(multiple) == 2


def test_error_and_success_examples():
    errors = cast(Mapping[str, Any], examples_module.ERROR_EXAMPLES)
    success = cast(Mapping[str, Any], examples_module.SUCCESS_EXAMPLES)
    rate_limit = errors["rate_limit_error"]["value"]
    assert rate_limit["severity"] == "warning"
    auth = errors["authentication_error"]["value"]
    assert auth["icon"] == "🔒"
    created = success["conversation_created"]["value"]
    assert created["status"] == "active"


def test_analytics_and_metrics_examples():
    analytics_examples = cast(Mapping[str, Any], examples_module.ANALYTICS_EXAMPLES)
    metrics_examples = cast(Mapping[str, Any], examples_module.METRICS_EXAMPLES)
    usage = analytics_examples["usage_stats_week"]["value"]
    assert usage["tokens"]["input"] > usage["tokens"]["output"]
    metrics = metrics_examples["full_metrics"]["value"]
    assert metrics["system"]["active_conversations"] == 15


def test_health_and_model_examples():
    health_examples = cast(Mapping[str, Any], examples_module.HEALTH_EXAMPLES)
    model_examples = cast(Mapping[str, Any], examples_module.MODEL_LIST_EXAMPLES)
    healthy = health_examples["healthy"]["value"]
    assert healthy["status"] == "healthy"
    models = model_examples["available_models"]["value"]
    assert "gpt-4o" in models


def test_agent_and_websocket_examples():
    agent_examples = cast(Mapping[str, Any], examples_module.AGENT_LIST_EXAMPLES)
    websocket_examples = cast(Mapping[str, Any], examples_module.WEBSOCKET_EXAMPLES)
    agents = agent_examples["available_agents"]["value"]
    assert "CodeActAgent" in agents
    ws = websocket_examples["agent_action"]["value"]
    assert ws["action"] == "FileEditAction"
