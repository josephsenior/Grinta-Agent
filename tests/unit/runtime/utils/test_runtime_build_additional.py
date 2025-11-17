from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import types
from pathlib import Path
from typing import Any, Type, cast

import pytest


ROOT = Path(__file__).resolve().parents[4]


# --- Stub dependencies before importing module under test ---

docker_mod = sys.modules.setdefault("docker", types.ModuleType("docker"))
if not hasattr(docker_mod, "from_env"):
    setattr(docker_mod, "from_env", lambda: object())

dirhash_mod = sys.modules.setdefault("dirhash", types.ModuleType("dirhash"))
if not hasattr(dirhash_mod, "dirhash"):

    def fake_dirhash(path: Any, hash_name: str, ignore: Any = None) -> str:
        return "feedbeef"

    setattr(dirhash_mod, "dirhash", fake_dirhash)

forge_root = Path(tempfile.mkdtemp(prefix="forge-runtime-tests-"))
forge_dir = forge_root / "forge_pkg"
forge_dir.mkdir()
(forge_dir / "__init__.py").write_text("# forge package\n")
(forge_dir / "pyproject.toml").write_text("[tool.poetry]\nname='forge'\n")
(forge_dir / "poetry.lock").write_text("lockfile\n")
(forge_root / "microagents").mkdir()
((forge_root / "microagents") / "agent.py").write_text("# agent\n")

forge_mod = sys.modules.setdefault("forge", types.ModuleType("forge"))
setattr(forge_mod, "__file__", str(forge_dir / "__init__.py"))
setattr(forge_mod, "__version__", "9.9.9")

exceptions_mod = sys.modules.setdefault(
    "forge.core.exceptions", types.ModuleType("forge.core.exceptions")
)
if not hasattr(exceptions_mod, "AgentRuntimeBuildError"):

    class _AgentRuntimeBuildError(RuntimeError):
        pass

    setattr(exceptions_mod, "AgentRuntimeBuildError", _AgentRuntimeBuildError)

logger_mod = sys.modules.setdefault(
    "forge.core.logger", types.ModuleType("forge.core.logger")
)


class DummyLogger:
    def debug(self, *args: Any, **kwargs: Any) -> None:
        pass

    def info(self, *args: Any, **kwargs: Any) -> None:
        pass

    def warning(self, *args: Any, **kwargs: Any) -> None:
        pass


setattr(logger_mod, "forge_logger", DummyLogger())

builder_mod = sys.modules.setdefault(
    "forge.runtime.builder", types.ModuleType("forge.runtime.builder")
)
if not hasattr(builder_mod, "RuntimeBuilder"):

    class _RuntimeBuilder:
        def image_exists(self, *args: Any, **kwargs: Any) -> bool:
            raise NotImplementedError

        def build(self, *args: Any, **kwargs: Any) -> str:
            raise NotImplementedError

    setattr(builder_mod, "RuntimeBuilder", _RuntimeBuilder)

if not hasattr(builder_mod, "DockerRuntimeBuilder"):

    class _DockerRuntimeBuilder(getattr(builder_mod, "RuntimeBuilder")):  # type: ignore[misc]
        def __init__(self, client: Any = None) -> None:
            self.client = client

    setattr(builder_mod, "DockerRuntimeBuilder", _DockerRuntimeBuilder)


# Import module under test
spec = importlib.util.spec_from_file_location(
    "forge.runtime.utils.runtime_build",
    ROOT / "forge" / "runtime" / "utils" / "runtime_build.py",
)
assert spec and spec.loader
runtime_build = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.runtime_build"] = runtime_build
spec.loader.exec_module(runtime_build)

BuildFromImageType = runtime_build.BuildFromImageType
AgentRuntimeBuildError: Type[Exception] = cast(
    Type[Exception], getattr(exceptions_mod, "AgentRuntimeBuildError")
)
RuntimeBuilderCls: Type[Any] = cast(Type[Any], getattr(builder_mod, "RuntimeBuilder"))


# --- Fixtures ---


@pytest.fixture(autouse=True)
def reset_env(monkeypatch):
    monkeypatch.delenv("OH_RUNTIME_RUNTIME_IMAGE_REPO", raising=False)


@pytest.fixture
def forge_fs(tmp_path, monkeypatch):
    forge_pkg = tmp_path / "forge_pkg"
    forge_pkg.mkdir()
    (forge_pkg / "__init__.py").write_text("# forge\n")
    (forge_pkg / "pyproject.toml").write_text("pyproject\n")
    (forge_pkg / "poetry.lock").write_text("poetry\n")
    microagents_dir = tmp_path / "microagents"
    microagents_dir.mkdir()
    (microagents_dir / "agent.txt").write_text("agent\n")
    monkeypatch.setattr(
        sys.modules["forge"], "__file__", str(forge_pkg / "__init__.py"), raising=False
    )
    return forge_pkg, microagents_dir


# --- Tests ---


def test_get_runtime_image_repo_from_env(monkeypatch):
    monkeypatch.setenv("OH_RUNTIME_RUNTIME_IMAGE_REPO", "custom/repo")
    assert runtime_build.get_runtime_image_repo() == "custom/repo"


def test_generate_dockerfile_uses_template(monkeypatch):
    captured = {}

    class DummyTemplate:
        def render(self, **context):
            captured.update(context)
            return "rendered dockerfile"

    class DummyEnv:
        def __init__(self, *args, **kwargs):
            captured["env_kwargs"] = kwargs

        def get_template(self, name):
            assert name == "Dockerfile.j2"
            return DummyTemplate()

    monkeypatch.setattr(runtime_build, "Environment", DummyEnv)
    result = runtime_build._generate_dockerfile(
        "ubuntu:latest",
        build_from=BuildFromImageType.VERSIONED,
        extra_deps="apt install",
        enable_browser=False,
    )
    assert result == "rendered dockerfile"
    assert captured["base_image"] == "ubuntu:latest"
    assert captured["build_from_versioned"] is True
    assert captured["extra_deps"] == "apt install"
    assert captured["enable_browser"] is False


def test_get_runtime_image_repo_and_tag_reuse(monkeypatch):
    monkeypatch.setenv("OH_RUNTIME_RUNTIME_IMAGE_REPO", "ghcr.io/all-hands-ai/runtime")
    repo, tag = runtime_build.get_runtime_image_repo_and_tag(
        "ghcr.io/all-hands-ai/runtime:abc"
    )
    assert repo == "ghcr.io/all-hands-ai/runtime"
    assert tag == "abc"


def test_get_runtime_image_repo_and_tag_new(monkeypatch):
    monkeypatch.setenv("OH_RUNTIME_RUNTIME_IMAGE_REPO", "ghcr.io/all-hands-ai/runtime")
    repo, tag = runtime_build.get_runtime_image_repo_and_tag("library/python:3.12")
    assert repo == "ghcr.io/all-hands-ai/runtime"
    assert tag.startswith("oh_v")


def test_get_runtime_image_repo_and_tag_handles_long_repo(monkeypatch):
    monkeypatch.setenv("OH_RUNTIME_RUNTIME_IMAGE_REPO", "ghcr.io/all-hands-ai/runtime")

    class LoggerCapture:
        def __init__(self):
            self.warning_called = False

        def debug(self, *args, **kwargs):
            pass

        def info(self, *args, **kwargs):
            pass

        def warning(self, *args, **kwargs):
            self.warning_called = True

    logger_capture = LoggerCapture()
    monkeypatch.setattr(runtime_build, "logger", logger_capture, raising=False)
    very_long_repo = "myorg/" + "a" * 10 + ":" + "b" * 200
    repo, tag = runtime_build.get_runtime_image_repo_and_tag(very_long_repo)
    assert repo == "ghcr.io/all-hands-ai/runtime"
    assert tag.startswith("oh_v")
    assert logger_capture.warning_called


def test_build_runtime_image_with_temp_folder(monkeypatch):
    calls = []

    def fake_build(**kwargs):
        calls.append(kwargs)
        return "result"

    monkeypatch.setattr(
        runtime_build, "build_runtime_image_in_folder", fake_build, raising=False
    )
    runtime_builder = RuntimeBuilderCls()
    result = runtime_build.build_runtime_image(
        "base", runtime_builder, build_folder=None
    )
    assert result == "result"
    assert isinstance(calls[0]["build_folder"], Path)


def test_build_runtime_image_delegates(monkeypatch, tmp_path):
    calls = []

    def fake_build(**kwargs):
        calls.append(kwargs)
        return "result"

    monkeypatch.setattr(
        runtime_build, "build_runtime_image_in_folder", fake_build, raising=False
    )
    runtime_builder = RuntimeBuilderCls()
    result = runtime_build.build_runtime_image(
        "base", runtime_builder, build_folder=str(tmp_path)
    )
    assert result == "result"
    assert calls[0]["base_image"] == "base"


def test_build_runtime_image_force_rebuild(monkeypatch, tmp_path):
    monkeypatch.setattr(
        runtime_build, "get_runtime_image_repo_and_tag", lambda base: ("repo", "tag")
    )
    monkeypatch.setattr(
        runtime_build, "get_hash_for_lock_files", lambda *args, **kwargs: "lockhash"
    )
    monkeypatch.setattr(
        runtime_build, "get_tag_for_versioned_image", lambda base: "verhash"
    )
    monkeypatch.setattr(
        runtime_build, "get_hash_for_source_files", lambda: "sourcehash"
    )

    prep_calls = []

    def capture_prep(build_folder, base_image, build_from, extra_deps, enable_browser):
        prep_calls.append(
            {
                "build_folder": build_folder,
                "base_image": base_image,
                "build_from": build_from,
                "extra_deps": extra_deps,
                "enable_browser": enable_browser,
            },
        )

    monkeypatch.setattr(runtime_build, "prep_build_folder", capture_prep, raising=False)

    build_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def record_build(*args: Any, **kwargs: Any) -> str:
        build_calls.append((args, kwargs))
        return "built-image"

    monkeypatch.setattr(
        runtime_build, "_build_sandbox_image", record_build, raising=False
    )

    class FakeBuilder(RuntimeBuilderCls):
        def image_exists(self, *args, **kwargs):
            return False

    builder = FakeBuilder()
    image = runtime_build.build_runtime_image_in_folder(
        base_image="ubuntu:latest",
        runtime_builder=builder,
        build_folder=tmp_path,
        extra_deps="pip install foo",
        dry_run=False,
        force_rebuild=True,
        platform="linux/amd64",
        enable_browser=True,
    )
    assert image == "repo:oh_v9.9.9_lockhash_sourcehash"
    assert prep_calls[0]["build_from"] is BuildFromImageType.SCRATCH
    assert build_calls, "build should be invoked when not dry run"


def test_build_runtime_image_force_rebuild_dry_run(monkeypatch, tmp_path):
    monkeypatch.setattr(
        runtime_build, "get_runtime_image_repo_and_tag", lambda base: ("repo", "tag")
    )
    monkeypatch.setattr(
        runtime_build, "get_hash_for_lock_files", lambda *args, **kwargs: "lockhash"
    )
    monkeypatch.setattr(
        runtime_build, "get_tag_for_versioned_image", lambda base: "verhash"
    )
    monkeypatch.setattr(
        runtime_build, "get_hash_for_source_files", lambda: "sourcehash"
    )
    monkeypatch.setattr(
        runtime_build, "prep_build_folder", lambda *args, **kwargs: None, raising=False
    )
    build_invoked: list[bool] = []

    def mark_invoked(*args: Any, **kwargs: Any) -> str:
        build_invoked.append(True)
        return "built"

    monkeypatch.setattr(
        runtime_build, "_build_sandbox_image", mark_invoked, raising=False
    )

    class FakeBuilder(RuntimeBuilderCls):
        def image_exists(self, *args, **kwargs):
            return False

    builder = FakeBuilder()
    image = runtime_build.build_runtime_image_in_folder(
        "ubuntu:latest",
        builder,
        tmp_path,
        extra_deps=None,
        dry_run=True,
        force_rebuild=True,
    )
    assert image == "repo:oh_v9.9.9_lockhash_sourcehash"
    assert not build_invoked, "build should not run when dry_run=True"


def test_build_runtime_image_reuses_existing(monkeypatch, tmp_path):
    monkeypatch.setattr(
        runtime_build, "get_runtime_image_repo_and_tag", lambda base: ("repo", "tag")
    )
    monkeypatch.setattr(
        runtime_build, "get_hash_for_lock_files", lambda *args, **kwargs: "lockhash"
    )
    monkeypatch.setattr(
        runtime_build, "get_tag_for_versioned_image", lambda base: "verhash"
    )
    monkeypatch.setattr(
        runtime_build, "get_hash_for_source_files", lambda: "sourcehash"
    )

    expected_hash = "repo:oh_v9.9.9_lockhash_sourcehash"

    class FakeBuilder(RuntimeBuilderCls):
        def image_exists(self, name, with_tag=True):
            if name == expected_hash and with_tag is False:
                return True
            return False

        def build(self, *args, **kwargs):
            return expected_hash

    builder = FakeBuilder()
    image = runtime_build.build_runtime_image_in_folder(
        "ubuntu:latest",
        builder,
        tmp_path,
        extra_deps=None,
        dry_run=False,
        force_rebuild=False,
    )
    assert image == expected_hash


def test_build_runtime_image_uses_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(
        runtime_build, "get_runtime_image_repo_and_tag", lambda base: ("repo", "tag")
    )
    monkeypatch.setattr(
        runtime_build, "get_hash_for_lock_files", lambda *args, **kwargs: "lockhash"
    )
    monkeypatch.setattr(
        runtime_build, "get_tag_for_versioned_image", lambda base: "verhash"
    )
    monkeypatch.setattr(
        runtime_build, "get_hash_for_source_files", lambda: "sourcehash"
    )
    prep_calls = []

    def capture_prep(build_folder, base_image, build_from, extra_deps, enable_browser):
        prep_calls.append(
            {
                "build_folder": build_folder,
                "base_image": base_image,
                "build_from": build_from,
                "extra_deps": extra_deps,
                "enable_browser": enable_browser,
            },
        )

    monkeypatch.setattr(runtime_build, "prep_build_folder", capture_prep, raising=False)
    monkeypatch.setattr(
        runtime_build,
        "_build_sandbox_image",
        lambda *args, **kwargs: "built",
        raising=False,
    )

    expected_hash = "repo:oh_v9.9.9_lockhash_sourcehash"
    lock_name = "repo:oh_v9.9.9_lockhash"

    class FakeBuilder(RuntimeBuilderCls):
        def image_exists(self, name, with_tag=True):
            if name == expected_hash and with_tag is False:
                return False
            if name == lock_name and with_tag is True:
                return True
            return False

        def build(self, *args, **kwargs):
            return expected_hash

    builder = FakeBuilder()
    image = runtime_build.build_runtime_image_in_folder(
        "ubuntu:latest",
        builder,
        tmp_path,
        extra_deps=None,
        dry_run=False,
        force_rebuild=False,
    )
    assert image == expected_hash
    assert prep_calls[0]["build_from"] is BuildFromImageType.LOCK
    assert prep_calls[0]["base_image"].endswith("lockhash")


def test_build_runtime_image_uses_versioned(monkeypatch, tmp_path):
    monkeypatch.setattr(
        runtime_build, "get_runtime_image_repo_and_tag", lambda base: ("repo", "tag")
    )
    monkeypatch.setattr(
        runtime_build, "get_hash_for_lock_files", lambda *args, **kwargs: "lockhash"
    )
    monkeypatch.setattr(
        runtime_build, "get_tag_for_versioned_image", lambda base: "verhash"
    )
    monkeypatch.setattr(
        runtime_build, "get_hash_for_source_files", lambda: "sourcehash"
    )
    monkeypatch.setattr(
        runtime_build, "prep_build_folder", lambda *args, **kwargs: None, raising=False
    )
    monkeypatch.setattr(
        runtime_build,
        "_build_sandbox_image",
        lambda *args, **kwargs: "built",
        raising=False,
    )

    expected_hash = "repo:oh_v9.9.9_lockhash_sourcehash"
    lock_name = "repo:oh_v9.9.9_lockhash"
    versioned_name = "repo:oh_v9.9.9_verhash"

    class FakeBuilder(RuntimeBuilderCls):
        def image_exists(self, name, with_tag=True):
            if name == expected_hash and with_tag is False:
                return False
            if name == lock_name and with_tag is True:
                return False
            if name == versioned_name and with_tag is True:
                return True
            return False

        def build(self, *args, **kwargs):
            return expected_hash

    builder = FakeBuilder()
    image = runtime_build.build_runtime_image_in_folder(
        "ubuntu:latest",
        builder,
        tmp_path,
        extra_deps=None,
        dry_run=False,
        force_rebuild=False,
    )
    assert image == expected_hash


def test_build_runtime_image_scratch(monkeypatch, tmp_path):
    monkeypatch.setattr(
        runtime_build, "get_runtime_image_repo_and_tag", lambda base: ("repo", "tag")
    )
    monkeypatch.setattr(
        runtime_build, "get_hash_for_lock_files", lambda *args, **kwargs: "lockhash"
    )
    monkeypatch.setattr(
        runtime_build, "get_tag_for_versioned_image", lambda base: "verhash"
    )
    monkeypatch.setattr(
        runtime_build, "get_hash_for_source_files", lambda: "sourcehash"
    )
    prep_calls = []

    def capture_prep(build_folder, base_image, build_from, extra_deps, enable_browser):
        prep_calls.append(
            {
                "build_folder": build_folder,
                "base_image": base_image,
                "build_from": build_from,
                "extra_deps": extra_deps,
                "enable_browser": enable_browser,
            },
        )

    monkeypatch.setattr(runtime_build, "prep_build_folder", capture_prep, raising=False)
    build_calls = []

    def fake_build(*args, **kwargs):
        build_calls.append((args, kwargs))
        return "built"

    monkeypatch.setattr(
        runtime_build, "_build_sandbox_image", fake_build, raising=False
    )

    class FakeBuilder(RuntimeBuilderCls):
        def image_exists(self, *args, **kwargs):
            return False

    builder = FakeBuilder()
    image = runtime_build.build_runtime_image_in_folder(
        "ubuntu:latest",
        builder,
        tmp_path,
        extra_deps="extras",
        dry_run=False,
        force_rebuild=False,
        enable_browser=False,
    )
    assert image == "repo:oh_v9.9.9_lockhash_sourcehash"
    build_args, build_kwargs = build_calls[0]
    assert build_kwargs["versioned_tag"] == "oh_v9.9.9_verhash"
    assert prep_calls[0]["build_from"] is BuildFromImageType.SCRATCH
    assert prep_calls[0]["extra_deps"] == "extras"


def test_prep_build_folder_copies(monkeypatch, tmp_path, forge_fs):
    copytree_calls = []
    copy2_calls = []
    monkeypatch.setattr(
        runtime_build.shutil,
        "copytree",
        lambda src, dst, ignore=None: copytree_calls.append(
            (Path(src), Path(dst), ignore)
        ),
        raising=False,
    )
    monkeypatch.setattr(
        runtime_build.shutil,
        "copy2",
        lambda src, dst: copy2_calls.append((Path(src), Path(dst))),
        raising=False,
    )
    monkeypatch.setattr(
        runtime_build,
        "_generate_dockerfile",
        lambda *args, **kwargs: "dockerfile",
        raising=False,
    )
    written = {}

    class DummyFile:
        def __init__(self, path):
            self.path = path

        def write(self, data):
            written[self.path] = data

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(
        runtime_build,
        "open",
        lambda path, mode, encoding=None: DummyFile(path),
        raising=False,
    )
    runtime_build.prep_build_folder(
        build_folder=tmp_path,
        base_image="ubuntu",
        build_from=BuildFromImageType.SCRATCH,
        extra_deps=None,
        enable_browser=True,
    )
    assert copytree_calls, "copytree should be called"
    assert copy2_calls, "copy2 should be called"
    assert any(
        Path(path).name == "Dockerfile" and data == "dockerfile"
        for path, data in written.items()
    )


def test_truncate_hash_shortens():
    result = runtime_build.truncate_hash("ffffffffffffffffffffffffffffffff")
    assert len(result) <= 16


def test_get_hash_for_lock_files_differs_without_browser(forge_fs, monkeypatch):
    forge_pkg, _ = forge_fs
    # Remove files in source dir to force fallback to parent directory
    for fname in ("pyproject.toml", "poetry.lock"):
        (forge_pkg / fname).unlink()
        (forge_pkg.parent / fname).write_text(f"{fname} content\n")

    with_browser = runtime_build.get_hash_for_lock_files("ubuntu", enable_browser=True)
    without_browser = runtime_build.get_hash_for_lock_files(
        "ubuntu", enable_browser=False
    )
    assert len(with_browser) <= 16
    assert with_browser != without_browser
    # Ensure fallback file path was used by checking hash refresh after modification
    (forge_pkg.parent / "pyproject.toml").write_text("modified\n")
    updated = runtime_build.get_hash_for_lock_files("ubuntu", enable_browser=True)
    assert updated != with_browser


def test_get_tag_for_versioned_image():
    tag = runtime_build.get_tag_for_versioned_image("Repo/Image:Tag")
    assert tag.endswith("_t_tag")


def test_get_hash_for_source_files(monkeypatch):
    monkeypatch.setattr(
        runtime_build, "dirhash", lambda *args, **kwargs: "abcd" * 8, raising=False
    )
    result = runtime_build.get_hash_for_source_files()
    assert len(result) <= 16


def test_build_sandbox_image_success(monkeypatch):
    class Builder(RuntimeBuilderCls):
        def __init__(self):
            self.calls = []

        def image_exists(self, name, with_tag=True):
            return False

        def build(self, path, tags, platform=None, extra_build_args=None):
            self.calls.append((path, tuple(tags), platform, extra_build_args))
            return tags[0]

    builder = Builder()
    name = runtime_build._build_sandbox_image(
        Path("/tmp/build"),
        builder,
        "repo",
        "src",
        "lock",
        "ver",
    )
    assert name == "repo:src"
    assert builder.calls


def test_build_sandbox_image_failure():
    class Builder(RuntimeBuilderCls):
        def image_exists(self, name, with_tag=True):
            return False

        def build(self, *args, **kwargs):
            return ""

    builder = Builder()
    with pytest.raises(AgentRuntimeBuildError):
        runtime_build._build_sandbox_image(
            Path("/tmp/build"),
            builder,
            "repo",
            "src",
            "lock",
            None,
        )
