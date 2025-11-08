"""Tests for AWS Bedrock helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from forge.llm import bedrock


def test_list_foundation_models_returns_prefixed_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_client = SimpleNamespace(
        list_foundation_models=lambda **kwargs: {
            "modelSummaries": [
                {"modelId": "meta.llama3"},
                {"modelId": "anthropic.claude"},
            ]
        }
    )
    monkeypatch.setattr("forge.llm.bedrock.boto3.client", lambda **kwargs: dummy_client)
    models = bedrock.list_foundation_models("us-west-2", "key", "secret")
    assert models == ["bedrock/meta.llama3", "bedrock/anthropic.claude"]


def test_list_foundation_models_handles_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("forge.llm.bedrock.boto3.client", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    models = bedrock.list_foundation_models("us", "key", "secret")
    assert models == []


def test_remove_error_modelId_filters_bedrock_models() -> None:
    models = ["bedrock/meta.llama", "openai/gpt-4o"]
    assert bedrock.remove_error_modelId(models) == ["openai/gpt-4o"]

