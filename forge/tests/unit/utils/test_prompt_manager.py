from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from forge.core.message import TextContent
from forge.utils import prompt


@pytest.fixture()
def template_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "system_prompt.j2").write_text("System: {{ info }}", encoding="utf-8")
    (tmp_path / "user_prompt.j2").write_text("User prompt", encoding="utf-8")
    (tmp_path / "additional_info.j2").write_text("Repo: {{ repository_info.repo_name }}", encoding="utf-8")
    (tmp_path / "microagent_info.j2").write_text("Agents: {{ triggered_agents|length }}", encoding="utf-8")

    fake_module = SimpleNamespace(refine_prompt=lambda text: text.upper())
    monkeypatch.setitem(sys.modules, "forge.agenthub.codeact_agent.tools.prompt", fake_module)
    return tmp_path


def test_prompt_manager_basic(template_dir: Path):
    manager = prompt.PromptManager(str(template_dir))
    assert manager.get_system_message(info="hello").startswith("SYSTEM")
    assert manager.get_example_user_message() == "User prompt"

    repo_info = prompt.RepositoryInfo(repo_name="repo")
    runtime = prompt.RuntimeInfo(date="today")
    instructions = prompt.ConversationInstructions(content="Do it")
    built = manager.build_workspace_context(repo_info, runtime, instructions, repo_instructions="follow")
    assert "Repo: repo" in built

    agents = [SimpleNamespace()]
    assert manager.build_microagent_info(agents).startswith("Agents: 1")


def test_prompt_manager_add_turns_left(template_dir: Path):
    manager = prompt.PromptManager(str(template_dir))

    class DummyMessage:
        def __init__(self, role: str, text: str) -> None:
            self.role = role
            self.content = [TextContent(text=text)]

    messages = [DummyMessage("assistant", "hi"), DummyMessage("user", "Task")]
    state = SimpleNamespace(iteration_flag=SimpleNamespace(max_value=5, current_value=2))
    manager.add_turns_left_reminder(messages, state)
    assert "turns left" in messages[-1].content[-1].text


def test_prompt_manager_missing_dir():
    with pytest.raises(ValueError):
        prompt.PromptManager(None)  # type: ignore[arg-type]

