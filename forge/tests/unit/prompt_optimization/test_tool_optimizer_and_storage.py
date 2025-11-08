from __future__ import annotations

import builtins
import shutil
from pathlib import Path
from typing import Any

import pytest

from forge.prompt_optimization.models import OptimizationConfig, PromptCategory, PromptVariant
from forge.prompt_optimization.optimizer import PromptOptimizer
from forge.prompt_optimization.registry import PromptRegistry
from forge.prompt_optimization.storage import PromptStorage
from forge.prompt_optimization.tool_optimizer import ToolOptimizer
from forge.prompt_optimization.tracker import PerformanceTracker


class _FunctionChunkStub:
    def __init__(self, name: str, description: str, parameters: dict[str, Any]):
        self.name = name
        self.description = description
        self.parameters = parameters


class _ToolParamStub:
    def __init__(self, type: str, function: _FunctionChunkStub):
        self.type = type
        self.function = function


@pytest.fixture
def prompt_optimizer() -> PromptOptimizer:
    registry = PromptRegistry()
    tracker = PerformanceTracker()
    config = OptimizationConfig(ab_split_ratio=0.1, min_samples_for_switch=0)
    return PromptOptimizer(registry, tracker, config)


def _install_tooling_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "forge.prompt_optimization.tool_optimizer.ChatCompletionToolParam", _ToolParamStub, raising=False
    )
    monkeypatch.setattr(
        "forge.prompt_optimization.tool_optimizer.ChatCompletionToolParamFunctionChunk",
        _FunctionChunkStub,
        raising=False,
    )


def test_tool_optimizer_creates_and_applies_variants(prompt_optimizer: PromptOptimizer, monkeypatch: pytest.MonkeyPatch) -> None:
    registry = prompt_optimizer.registry
    tracker = prompt_optimizer.tracker
    tool_optimizer = ToolOptimizer(registry, tracker, prompt_optimizer)
    tool_optimizer.tool_prompt_ids = {"demo": "tool_demo"}

    _install_tooling_stubs(monkeypatch)

    original_tool = _ToolParamStub(
        type="function",
        function=_FunctionChunkStub(
            name="demo",
            description="Original description",
            parameters={"properties": {"arg": {"description": "orig"}}},
        ),
    )

    created_ids = tool_optimizer.create_tool_variants(
        "demo",
        original_description="Original description",
        original_parameters={"properties": {"arg": {"description": "orig"}}},
    )
    assert created_ids

    improved_content = """DESCRIPTION: Updated description
PARAMETERS:
- arg
  description: better detail
"""

    challenger_id = prompt_optimizer.add_variant(
        prompt_id="tool_demo",
        content=improved_content,
        category=PromptCategory.TOOL_PROMPT,
    )
    prompt_optimizer.start_testing_variant("tool_demo", challenger_id)
    registry.get_variant(challenger_id).composite_score = 0.9  # type: ignore[attr-defined]
    registry.get_variant(created_ids[0]).composite_score = 0.1  # type: ignore[attr-defined]

    monkeypatch.setattr("forge.prompt_optimization.optimizer.random.random", lambda: 0.5)
    optimized_tool = tool_optimizer.optimize_tool(original_tool, "demo")
    assert isinstance(optimized_tool, _ToolParamStub)
    assert optimized_tool.function.description == "Updated description"
    param_description = optimized_tool.function.parameters["properties"]["arg"]["description"]
    if isinstance(param_description, dict):
        assert param_description.get("description") == "better detail"
    else:
        assert param_description == "better detail"

    status = tool_optimizer.get_tool_optimization_status("demo")
    assert status["prompt_id"] == "tool_demo"

    forced_id = tool_optimizer.force_optimize_tool("demo", "Force desc", {"properties": {}})
    assert forced_id is not None
    assert registry.get_active_variant("tool_demo").id == forced_id

    tool_optimizer.track_tool_execution("demo", success=True, execution_time=0.5)
    summary = tool_optimizer.get_tool_performance_summary()
    assert "demo" in summary

    all_status = tool_optimizer.get_all_tool_status()
    assert all_status["demo"]["prompt_id"] == "tool_demo"

    monkeypatch.setattr(prompt_optimizer, "should_evolve_prompt", lambda pid: True)
    monkeypatch.setattr(
        prompt_optimizer,
        "get_candidates_for_evolution",
        lambda pid: [registry.get_variant(challenger_id)],
    )

    class _DummyEvolver:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def evolve_prompt(self, prompt_id: str, max_variants: int = 3) -> list[str]:
            return ["demo-evolved"]

    monkeypatch.setattr(
        "forge.prompt_optimization.tool_optimizer.PromptEvolver",
        _DummyEvolver,
        raising=False,
    )
    monkeypatch.setattr(
        "forge.prompt_optimization.evolver.PromptEvolver",
        _DummyEvolver,
        raising=False,
    )

    assert tool_optimizer.evolve_tool("demo") == ["demo-evolved"]


def test_prompt_storage_persists_registry(tmp_path: Path) -> None:
    storage_dir = tmp_path / "opt_storage"
    config = OptimizationConfig(storage_path=str(storage_dir), auto_save=True, sync_interval=2)
    registry = PromptRegistry()
    tracker = PerformanceTracker()
    storage = PromptStorage(config, registry, tracker)

    prompt_id = "prompt-storage"
    variant_id = registry.register_variant(PromptVariant(content="initial", prompt_id=prompt_id))
    tracker.record_execution(
        variant_id=variant_id,
        prompt_id=prompt_id,
        category=PromptCategory.CUSTOM,
        success=True,
        execution_time=1.0,
    )

    storage.auto_save()
    storage.auto_save()  # trigger sync interval save
    assert (storage_dir / "registry.json").exists()

    storage_info = storage.get_storage_info()
    assert storage_info["files_exist"]["registry"] is True
    assert storage.force_save() is True

    # Load into a fresh registry/tracker pair
    new_registry = PromptRegistry()
    new_tracker = PerformanceTracker()
    new_config = OptimizationConfig(storage_path=str(storage_dir), auto_save=True, sync_interval=2)
    PromptStorage(new_config, new_registry, new_tracker)
    loaded_variant = new_registry.get_variant(variant_id)
    assert loaded_variant is not None
    assert loaded_variant.content == "initial"

    export_dir = tmp_path / "export"
    storage.export_data(str(export_dir))
    assert (export_dir / "registry.json").exists()

    backup_dir = tmp_path / "backup"
    assert storage.backup_data(str(backup_dir)) is True
    assert storage.restore_from_backup(str(backup_dir)) is True

    data_size = storage.get_data_size()
    assert data_size["total"] >= 0

    assert storage.import_data(str(export_dir)) is True
    assert storage.cleanup_old_data(days_to_keep=1) is False

    storage.clear_all_data()
    assert not (storage_dir / "registry.json").exists()


def test_tool_optimizer_returns_original_when_mapping_missing(prompt_optimizer: PromptOptimizer) -> None:
    registry = prompt_optimizer.registry
    tracker = prompt_optimizer.tracker
    tool_optimizer = ToolOptimizer(registry, tracker, prompt_optimizer)
    tool = _ToolParamStub("function", _FunctionChunkStub("missing", "desc", {"properties": {}}))
    assert tool_optimizer.optimize_tool(tool, "missing") is tool


def test_tool_optimizer_without_optimizer(prompt_optimizer: PromptOptimizer) -> None:
    registry = prompt_optimizer.registry
    tracker = prompt_optimizer.tracker
    tool_optimizer = ToolOptimizer(registry, tracker, prompt_optimizer)
    tool_optimizer.optimizer = None  # type: ignore[assignment]
    tool = _ToolParamStub("function", _FunctionChunkStub("demo", "desc", {"properties": {}}))
    assert tool_optimizer.optimize_tool(tool, "demo") is tool


def test_tool_optimizer_track_tool_execution_missing_variant(prompt_optimizer: PromptOptimizer) -> None:
    registry = prompt_optimizer.registry
    tracker = prompt_optimizer.tracker
    tool_optimizer = ToolOptimizer(registry, tracker, prompt_optimizer)
    tool_optimizer.tool_prompt_ids = {"demo": "prompt"}
    tool_optimizer.track_tool_execution("demo", success=True, execution_time=0.1)


def test_tool_optimizer_force_optimize_tool_missing_prompt(prompt_optimizer: PromptOptimizer) -> None:
    registry = prompt_optimizer.registry
    tracker = prompt_optimizer.tracker
    tool_optimizer = ToolOptimizer(registry, tracker, prompt_optimizer)
    assert tool_optimizer.force_optimize_tool("missing", "desc", {}) is None


def test_prompt_storage_save_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    storage_dir = tmp_path / "fail_storage"
    config = OptimizationConfig(storage_path=str(storage_dir))
    storage = PromptStorage(config, PromptRegistry(), PerformanceTracker())

    def _raise_io(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("builtins.open", _raise_io)
    assert storage.save_all() is False


def test_prompt_storage_load_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    storage_dir = tmp_path / "fail_load"
    config = OptimizationConfig(storage_path=str(storage_dir))
    storage = PromptStorage(config, PromptRegistry(), PerformanceTracker())

    target_file = storage.registry_file
    target_file.write_text("{}", encoding="utf-8")

    original_open = builtins.open

    def _raise_io(path, *args, **kwargs):
        if Path(path) == target_file:
            raise OSError("unreadable")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", _raise_io, raising=False)
    assert storage.load_all() is False


class _TrackerWithUpdate(PerformanceTracker):
    def _update_variant_metrics_from_performances(self, variant_id: str) -> None:  # pragma: no cover - helper
        self._variant_metrics.pop(variant_id, None)


def test_prompt_storage_cleanup_old_data_success(tmp_path: Path) -> None:
    storage_dir = tmp_path / "cleanup"
    config = OptimizationConfig(storage_path=str(storage_dir))
    registry = PromptRegistry()
    tracker = _TrackerWithUpdate()
    storage = PromptStorage(config, registry, tracker)

    prompt_id = "prompt"
    variant_id = registry.register_variant(PromptVariant(content="body", prompt_id=prompt_id))
    tracker.record_execution(
        variant_id=variant_id,
        prompt_id=prompt_id,
        category=PromptCategory.CUSTOM,
        success=True,
        execution_time=1.0,
    )
    for performance in tracker._performance_data:
        performance.timestamp = performance.timestamp.replace(year=performance.timestamp.year - 1)

    assert storage.cleanup_old_data(days_to_keep=30) is True


def test_tool_optimizer_optimize_handles_missing_variant(prompt_optimizer: PromptOptimizer, monkeypatch: pytest.MonkeyPatch) -> None:
    registry = prompt_optimizer.registry
    tracker = prompt_optimizer.tracker
    tool_optimizer = ToolOptimizer(registry, tracker, prompt_optimizer)
    tool_optimizer.tool_prompt_ids = {"demo": "prompt"}
    _install_tooling_stubs(monkeypatch)
    tool = _ToolParamStub("function", _FunctionChunkStub("demo", "desc", {"properties": {}}))

    monkeypatch.setattr(prompt_optimizer, "select_variant", lambda *args, **kwargs: None)
    assert tool_optimizer.optimize_tool(tool, "demo") is tool


def test_tool_optimizer_optimize_handles_exception(prompt_optimizer: PromptOptimizer, monkeypatch: pytest.MonkeyPatch) -> None:
    registry = prompt_optimizer.registry
    tracker = prompt_optimizer.tracker
    tool_optimizer = ToolOptimizer(registry, tracker, prompt_optimizer)
    tool_optimizer.tool_prompt_ids = {"demo": "prompt"}
    _install_tooling_stubs(monkeypatch)
    tool = _ToolParamStub("function", _FunctionChunkStub("demo", "desc", {"properties": {}}))

    monkeypatch.setattr(prompt_optimizer, "select_variant", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("fail")))
    assert tool_optimizer.optimize_tool(tool, "demo") is tool


def test_tool_optimizer_get_status_without_optimizer(prompt_optimizer: PromptOptimizer) -> None:
    registry = prompt_optimizer.registry
    tracker = prompt_optimizer.tracker
    tool_optimizer = ToolOptimizer(registry, tracker, prompt_optimizer)
    tool_optimizer.optimizer = None  # type: ignore[assignment]
    assert tool_optimizer.get_tool_optimization_status("demo") == {"status": "not_optimized"}
    assert tool_optimizer.get_all_tool_status() == {}


def test_tool_optimizer_track_tool_execution_failure(prompt_optimizer: PromptOptimizer, monkeypatch: pytest.MonkeyPatch) -> None:
    registry = prompt_optimizer.registry
    tracker = prompt_optimizer.tracker
    tool_optimizer = ToolOptimizer(registry, tracker, prompt_optimizer)
    tool_optimizer.tool_prompt_ids = {"demo": "prompt"}

    def _raise(*args, **kwargs):
        raise RuntimeError("fail")

    monkeypatch.setattr(prompt_optimizer, "record_execution", _raise)
    tool_optimizer.track_tool_execution("demo", success=True, execution_time=0.1)


def test_tool_optimizer_get_status_missing_prompt(prompt_optimizer: PromptOptimizer) -> None:
    tool_optimizer = ToolOptimizer(prompt_optimizer.registry, prompt_optimizer.tracker, prompt_optimizer)
    assert tool_optimizer.get_tool_optimization_status("missing") == {"status": "not_optimized"}


def test_prompt_storage_auto_save_disabled(tmp_path: Path) -> None:
    config = OptimizationConfig(storage_path=str(tmp_path), auto_save=False)
    storage = PromptStorage(config, PromptRegistry(), PerformanceTracker())
    assert storage.auto_save() is True


def test_prompt_storage_backup_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    storage_dir = tmp_path / "backup"
    config = OptimizationConfig(storage_path=str(storage_dir))
    storage = PromptStorage(config, PromptRegistry(), PerformanceTracker())
    storage.registry_file.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(shutil, "copy2", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("fail")))
    assert storage.backup_data(str(storage_dir / "dest")) is False


def test_prompt_storage_restore_missing_path(tmp_path: Path) -> None:
    storage = PromptStorage(OptimizationConfig(storage_path=str(tmp_path)), PromptRegistry(), PerformanceTracker())
    assert storage.restore_from_backup(str(tmp_path / "missing")) is False


def test_prompt_storage_export_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    storage_dir = tmp_path / "export"
    config = OptimizationConfig(storage_path=str(storage_dir))
    storage = PromptStorage(config, PromptRegistry(), PerformanceTracker())

    def _raise_open(path, *args, **kwargs):
        raise OSError("fail")

    monkeypatch.setattr("builtins.open", _raise_open)
    assert storage.export_data(str(tmp_path / "dest")) is False


def test_prompt_storage_import_missing_path(tmp_path: Path) -> None:
    storage = PromptStorage(OptimizationConfig(storage_path=str(tmp_path)), PromptRegistry(), PerformanceTracker())
    assert storage.import_data(str(tmp_path / "missing")) is False

