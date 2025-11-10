from __future__ import annotations

import pytest
from pydantic import SecretStr

import forge.integrations.service_types as service_types
from forge.integrations.provider import CustomSecret, ProviderToken
from forge.integrations.service_types import ProviderType, SuggestedTask, TaskType


class TemplateRecorder:
    def __init__(self, name: str, store: list[dict[str, dict]]) -> None:
        self.name = name
        self._store = store

    def render(self, **kwargs) -> str:
        self._store.append({"name": self.name, "kwargs": kwargs})
        return f"render-{self.name}"


class EnvRecorder:
    def __init__(self) -> None:
        self.requested_templates: list[str] = []
        self.render_calls: list[dict[str, dict]] = []
        self._templates: dict[str, TemplateRecorder] = {}

    def get_template(self, name: str) -> TemplateRecorder:
        self.requested_templates.append(name)
        if name not in self._templates:
            self._templates[name] = TemplateRecorder(name, self.render_calls)
        return self._templates[name]


def _make_task(provider: ProviderType, task_type: TaskType) -> SuggestedTask:
    return SuggestedTask(
        git_provider=provider,
        task_type=task_type,
        repo="acme/widgets",
        issue_number=42,
        title="Fix widgets",
    )


def test_provider_token_from_value_handles_none_token() -> None:
    token = ProviderToken.from_value({"token": None, "user_id": "someone"})
    assert token.token.get_secret_value() == ""
    assert token.user_id == "someone"
    assert token.host is None


def test_provider_token_from_value_instance_returns_same() -> None:
    original = ProviderToken(token=SecretStr("existing"), user_id="me")
    derived = ProviderToken.from_value(original)
    assert derived is original


def test_provider_token_from_value_invalid_type() -> None:
    with pytest.raises(ValueError):
        ProviderToken.from_value(123)  # type: ignore[arg-type]


def test_custom_secret_from_value_with_defaults() -> None:
    secret = CustomSecret.from_value({})
    assert secret.secret.get_secret_value() == ""
    assert secret.description == ""


def test_custom_secret_from_value_instance_returns_same() -> None:
    existing = CustomSecret(secret=SecretStr("secret"), description="already")
    result = CustomSecret.from_value(existing)
    assert result is existing


def test_custom_secret_from_value_invalid_type() -> None:
    with pytest.raises(ValueError):
        CustomSecret.from_value(42)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("provider", "token_env_var", "request_type_short", "request_verb"),
    [
        (ProviderType.GITHUB, "GITHUB_TOKEN", "PR", "pull request"),
        (ProviderType.GITLAB, "GITLAB_TOKEN", "MR", "merge request"),
        (ProviderType.BITBUCKET, "BITBUCKET_TOKEN", "PR", "pull request"),
    ],
)
def test_suggested_task_get_provider_terms(provider, token_env_var, request_type_short, request_verb) -> None:
    task = _make_task(provider, TaskType.OPEN_ISSUE)
    terms = task.get_provider_terms()
    assert terms["tokenEnvVar"] == token_env_var
    assert terms["requestTypeShort"] == request_type_short
    assert terms["requestVerb"] == request_verb


def test_suggested_task_get_provider_terms_invalid_provider() -> None:
    task = _make_task(ProviderType.ENTERPRISE_SSO, TaskType.OPEN_ISSUE)
    with pytest.raises(ValueError):
        task.get_provider_terms()


@pytest.mark.parametrize(
    ("task_type", "template_name"),
    [
        (TaskType.MERGE_CONFLICTS, "merge_conflict_prompt.j2"),
        (TaskType.FAILING_CHECKS, "failing_checks_prompt.j2"),
        (TaskType.UNRESOLVED_COMMENTS, "unresolved_comments_prompt.j2"),
        (TaskType.OPEN_ISSUE, "open_issue_prompt.j2"),
    ],
)
def test_suggested_task_get_prompt_uses_expected_template(
    monkeypatch: pytest.MonkeyPatch,
    task_type: TaskType,
    template_name: str,
) -> None:
    env = EnvRecorder()
    monkeypatch.setattr(service_types, "Environment", lambda *args, **kwargs: env)
    monkeypatch.setattr(service_types, "FileSystemLoader", lambda *args, **kwargs: object())

    task = _make_task(ProviderType.GITHUB, task_type)

    rendered = task.get_prompt_for_task()

    assert rendered == f"render-{template_name}"
    assert env.requested_templates == [template_name]
    assert len(env.render_calls) == 1
    render_kwargs = env.render_calls[0]["kwargs"]
    assert render_kwargs["issue_number"] == 42
    assert render_kwargs["repo"] == "acme/widgets"
    assert render_kwargs["tokenEnvVar"] == "GITHUB_TOKEN"


def test_suggested_task_get_prompt_unsupported_task(monkeypatch: pytest.MonkeyPatch) -> None:
    env = EnvRecorder()
    monkeypatch.setattr(service_types, "Environment", lambda *args, **kwargs: env)
    monkeypatch.setattr(service_types, "FileSystemLoader", lambda *args, **kwargs: object())

    task = _make_task(ProviderType.GITHUB, TaskType.OPEN_PR)

    with pytest.raises(ValueError):
        task.get_prompt_for_task()

