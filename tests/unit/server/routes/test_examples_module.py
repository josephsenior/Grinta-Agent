"""Tests for OpenAPI examples module."""

from __future__ import annotations

from forge.server.routes import examples as examples_module


def test_settings_examples_structure():
    assert "basic_settings" in examples_module.SETTINGS_EXAMPLES
    basic = examples_module.SETTINGS_EXAMPLES["basic_settings"]
    assert basic["value"]["llm"]["model"].startswith("anthropic/")
    advanced = examples_module.SETTINGS_EXAMPLES["advanced_settings"]
    assert advanced["value"]["security"]["confirmation_mode"] is True


def test_conversation_examples_variants():
    examples = examples_module.CONVERSATION_EXAMPLES
    assert {"simple_conversation", "with_repository", "metasop_orchestration"} <= set(examples)
    assert "github_repo" in examples["with_repository"]["value"]


def test_file_upload_examples():
    single = examples_module.FILE_UPLOAD_EXAMPLES["single_file"]["value"]
    assert single["content"].startswith("flask==")
    multiple = examples_module.FILE_UPLOAD_EXAMPLES["multiple_files"]["value"]["files"]
    assert len(multiple) == 2


def test_error_and_success_examples():
    rate_limit = examples_module.ERROR_EXAMPLES["rate_limit_error"]["value"]
    assert rate_limit["severity"] == "warning"
    auth = examples_module.ERROR_EXAMPLES["authentication_error"]["value"]
    assert auth["icon"] == "🔒"
    created = examples_module.SUCCESS_EXAMPLES["conversation_created"]["value"]
    assert created["status"] == "active"


def test_analytics_and_metrics_examples():
    usage = examples_module.ANALYTICS_EXAMPLES["usage_stats_week"]["value"]
    assert usage["tokens"]["input"] > usage["tokens"]["output"]
    metrics = examples_module.METRICS_EXAMPLES["full_metrics"]["value"]
    assert metrics["system"]["active_conversations"] == 15


def test_health_and_model_examples():
    healthy = examples_module.HEALTH_EXAMPLES["healthy"]["value"]
    assert healthy["status"] == "healthy"
    models = examples_module.MODEL_LIST_EXAMPLES["available_models"]["value"]
    assert "gpt-4o" in models


def test_agent_and_websocket_examples():
    agents = examples_module.AGENT_LIST_EXAMPLES["available_agents"]["value"]
    assert "CodeActAgent" in agents
    ws = examples_module.WEBSOCKET_EXAMPLES["agent_action"]["value"]
    assert ws["action"] == "FileEditAction"
