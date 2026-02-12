"""Renamed from test_setup.py to avoid basename clash with tests/unit/runtime/test_setup.py.

Original content preserved. See issue: duplicate collection causing import file mismatch on Windows.

"""

from unittest.mock import patch
from conftest import _load_runtime
from backend.core.setup import initialize_repository_for_runtime
from backend.events.action import FileReadAction, FileWriteAction
from backend.events.observation import FileReadObservation, FileWriteObservation
from backend.integrations.service_types import ProviderType, Repository


def test_initialize_repository_for_runtime(temp_dir, runtime_cls, run_as_Forge):
    """Test that the initialize_repository_for_runtime function works."""
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    mock_repo = Repository(
        id="1232",
        full_name="Forge/Forge",
        git_provider=ProviderType.GITHUB,
        is_public=True,
    )
    with patch(
        "backend.runtime.base.ProviderHandler.verify_repo_provider",
        return_value=mock_repo,
    ):
        repository_dir = initialize_repository_for_runtime(
            runtime, selected_repository="Forge/Forge"
        )
    assert repository_dir is not None
    assert repository_dir == "forge"


def test_maybe_run_setup_script(temp_dir, runtime_cls, run_as_Forge):
    """Test that setup script is executed when it exists."""
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    setup_script = ".Forge/setup.sh"
    write_obs = runtime.write(
        FileWriteAction(
            path=setup_script, content="#!/bin/bash\necho 'Hello World' >> README.md\n"
        )
    )
    assert isinstance(write_obs, FileWriteObservation)
    runtime.maybe_run_setup_script()
    read_obs = runtime.read(FileReadAction(path="README.md"))
    assert isinstance(read_obs, FileReadObservation)
    assert read_obs.content == "Hello World\n"


def test_maybe_run_setup_script_with_long_timeout(temp_dir, runtime_cls, run_as_Forge):
    """Test that setup script is executed when it exists (long timeout path)."""
    runtime, config = _load_runtime(
        temp_dir,
        runtime_cls,
        run_as_Forge,
        runtime_startup_env_vars={"NO_CHANGE_TIMEOUT_SECONDS": "1"},
    )
    setup_script = ".Forge/setup.sh"
    write_obs = runtime.write(
        FileWriteAction(
            path=setup_script,
            content="#!/bin/bash\nsleep 3 && echo 'Hello World' >> README.md\n",
        )
    )
    assert isinstance(write_obs, FileWriteObservation)
    runtime.maybe_run_setup_script()
    read_obs = runtime.read(FileReadAction(path="README.md"))
    assert isinstance(read_obs, FileReadObservation)
    assert read_obs.content == "Hello World\n"

