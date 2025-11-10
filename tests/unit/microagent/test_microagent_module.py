from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from forge.core.exceptions import MicroagentValidationError
from forge.microagent import microagent as micro_module
from forge.microagent.microagent import (
    BaseMicroagent,
    KnowledgeMicroagent,
    MicroagentMetadata,
    MicroagentType,
    RepoMicroagent,
    TaskMicroagent,
    _collect_markdown_files,
    _collect_special_files,
    _finalize_loaded_microagent,
    _infer_microagent_type,
    load_microagents_from_dir,
)
from forge.microagent.types import InputMetadata


def test_finalize_loaded_microagent_validates_type() -> None:
    metadata = {"name": "demo", "version": 1.2, "type": "knowledge"}
    finalized = _finalize_loaded_microagent(metadata, Path("demo.md"))
    assert finalized.version == "1.2"

    with pytest.raises(MicroagentValidationError):
        _finalize_loaded_microagent({"name": "demo", "type": "invalid"}, Path("demo.md"))


def test_infer_microagent_type_updates_triggers() -> None:
    knowledge_metadata = MicroagentMetadata(name="demo", triggers=["/demo"])
    assert _infer_microagent_type(knowledge_metadata) is MicroagentType.KNOWLEDGE

    task_metadata = MicroagentMetadata(name="runner", inputs=[InputMetadata(name="arg", description="desc")])
    inferred = _infer_microagent_type(task_metadata)
    assert inferred is MicroagentType.TASK
    assert "/runner" in task_metadata.triggers


def _write_microagent_file(tmp_path: Path, relative: str, body: str) -> Path:
    file_path = tmp_path / relative
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(body, encoding="utf-8")
    return file_path


def test_base_microagent_loads_from_frontmatter(tmp_path: Path) -> None:
    microagent_dir = tmp_path / ".Forge" / "microagents"
    content = textwrap.dedent(
        """\
        ---
        name: helper
        triggers:
          - assist
        ---
        content body
        """
    )
    file_path = _write_microagent_file(microagent_dir, "helper.md", content)

    agent = BaseMicroagent.load(file_path, microagent_dir=microagent_dir)
    assert agent.name == "helper"
    assert agent.metadata.name == "helper"
    assert agent.type is MicroagentType.KNOWLEDGE
    assert agent.source.endswith("helper.md")


def test_task_microagent_appends_prompt() -> None:
    metadata = MicroagentMetadata(
        name="tasker",
        inputs=[InputMetadata(name="project", description="Name of project")],
        type=MicroagentType.TASK,
    )
    agent = TaskMicroagent(name="tasker", content="Task body with ${project}", metadata=metadata, source="path", type=MicroagentType.TASK)
    assert "ask the user to provide them" in agent.content
    assert agent.requires_user_input() is True
    assert agent.extract_variables("Here is ${value}") == ["value"]


def test_collect_helpers_ignore_missing(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".cursorrules").write_text("rules", encoding="utf-8")
    (repo_root / "AGENTS.md").write_text("agents", encoding="utf-8")

    special = _collect_special_files(repo_root)
    assert any(path.name.lower() == ".cursorrules" for path in special)
    assert any("agents" in path.name.lower() for path in special)

    micro_dir = repo_root / ".Forge" / "microagents"
    _write_microagent_file(micro_dir, "nested/agent.md", "content")
    _write_microagent_file(micro_dir, "README.md", "ignore me")

    collected = _collect_markdown_files(micro_dir)
    assert all(path.name != "README.md" for path in collected)
    assert any("agent.md" in path.name for path in collected)


def test_load_microagents_from_dir(tmp_path: Path) -> None:
    microagent_dir = tmp_path / ".Forge" / "microagents"
    repo_root = microagent_dir.parent.parent
    repo_root.mkdir(parents=True, exist_ok=True)
    microagent_dir.mkdir(parents=True, exist_ok=True)

    (repo_root / ".cursorrules").write_text(
        "---\nname: repo_name\n---\nRepository specific notes\n",
        encoding="utf-8",
    )

    knowledge_content = textwrap.dedent(
        """\
        ---
        name: helper
        triggers: ["help"]
        ---
        Body
        """
    )
    _write_microagent_file(microagent_dir, "knowledge.md", knowledge_content)

    repo_agents, knowledge_agents = load_microagents_from_dir(microagent_dir)
    assert "cursorrules" in repo_agents
    assert "knowledge" in knowledge_agents
    assert isinstance(repo_agents["cursorrules"], RepoMicroagent)
    assert isinstance(knowledge_agents["knowledge"], KnowledgeMicroagent)


def test_load_single_microagent_reports_errors(tmp_path: Path) -> None:
    microagent_dir = tmp_path / ".Forge" / "microagents"
    microagent_dir.mkdir(parents=True, exist_ok=True)
    bad_path = _write_microagent_file(
        microagent_dir,
        "bad.md",
        "---\nname: bad\ntype: invalid\n---\ncontent\n",
    )

    with pytest.raises(MicroagentValidationError):
        micro_module._load_single_microagent(bad_path, microagent_dir)


def test_knowledge_microagent_trigger_matching() -> None:
    metadata = MicroagentMetadata(name="knowledge", triggers=["hello", "world"])
    agent = KnowledgeMicroagent(
        name="knowledge",
        content="info",
        metadata=metadata,
        source="path",
        type=MicroagentType.KNOWLEDGE,
    )
    assert agent.match_trigger("Say hello there") == "hello"
    assert agent.match_trigger("no match") is None


def test_task_microagent_without_placeholders() -> None:
    metadata = MicroagentMetadata(name="task", inputs=[], triggers=[])
    agent = TaskMicroagent(
        name="task",
        content="Task without variables",
        metadata=metadata,
        source="path",
        type=MicroagentType.TASK,
    )
    assert agent.requires_user_input() is False


def test_collect_markdown_files_missing_dir(tmp_path: Path) -> None:
    missing_dir = tmp_path / "missing"
    assert _collect_markdown_files(missing_dir) == []


def test_handle_third_party_creates_repo_agent(tmp_path: Path) -> None:
    path = tmp_path / ".cursorrules"
    path.write_text("rules", encoding="utf-8")
    agent = BaseMicroagent._handle_third_party(path, "rules")
    assert isinstance(agent, RepoMicroagent)
    assert agent.name == "cursorrules"


def test_derive_microagent_name_fallback_relpath(tmp_path: Path) -> None:
    microagent_dir = tmp_path / "microagents"
    microagent_dir.mkdir()
    external_file = tmp_path / "external.md"
    external_file.write_text("content", encoding="utf-8")
    derived = BaseMicroagent._derive_microagent_name(external_file, microagent_dir)
    assert derived is not None
    assert derived.endswith("external")


def test_derive_microagent_name_returns_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    microagent_dir = tmp_path / "microagents"
    microagent_dir.mkdir()
    target = tmp_path / "file.md"
    target.write_text("content", encoding="utf-8")

    monkeypatch.setattr("os.path.relpath", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("fail")))
    assert BaseMicroagent._derive_microagent_name(target, microagent_dir) is None


def test_load_file_content_prefers_argument(tmp_path: Path) -> None:
    file_path = tmp_path / "file.md"
    file_path.write_text("from disk", encoding="utf-8")
    assert BaseMicroagent._load_file_content(file_path, "override") == "override"


def test_create_microagent_instance_invalid_type(tmp_path: Path) -> None:
    metadata = MicroagentMetadata(name="demo")
    with pytest.raises(ValueError):
        BaseMicroagent._create_microagent_instance(
            derived_name=None,
            content="content",
            metadata=metadata,
            path=tmp_path / "demo.md",
            inferred_type=None,  # type: ignore[arg-type]
        )


def test_load_handles_legacy_instructions(tmp_path: Path) -> None:
    instructions = tmp_path / ".FORGE_instructions"
    instructions.write_text("legacy", encoding="utf-8")
    agent = BaseMicroagent.load(instructions)
    assert isinstance(agent, RepoMicroagent)
    assert agent.name == "repo_legacy"


def test_load_single_microagent_generic_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    path = tmp_path / "agent.md"
    path.write_text("---\nname: a\n---\n", encoding="utf-8")

    monkeypatch.setattr("forge.microagent.microagent.BaseMicroagent.load", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))

    with pytest.raises(ValueError) as exc:
        micro_module._load_single_microagent(path, tmp_path)
    assert "Error loading microagent" in str(exc.value)


def test_resolve_path_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    class _PathStub(Path):
        _flavour = Path(".")._flavour  # type: ignore[attr-defined]

        def resolve(self):  # type: ignore[override]
            raise OSError("fail")

    stub = _PathStub("relative.md")
    resolved = BaseMicroagent._resolve_path(stub)
    assert isinstance(resolved, Path)

