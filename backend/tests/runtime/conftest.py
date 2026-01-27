import os
import random
import shutil
import stat
import time
import pytest
from pytest import TempPathFactory
from forge.core.config import MCPConfig, ForgeConfig, load_FORGE_config
from forge.core.logger import forge_logger as logger
from forge.events import EventStream
from forge.llm.llm_registry import LLMRegistry
from forge.runtime.base import Runtime
from forge.runtime.impl.local.local_runtime_inprocess import LocalRuntime
from forge.runtime.plugins import AgentSkillsRequirement
from forge.storage import get_file_store
from forge.utils.async_utils import call_async_from_sync

TEST_IN_CI = os.getenv("TEST_IN_CI", "False").lower() in ["true", "1", "yes"]
RUN_AS_Forge = os.getenv("RUN_AS_Forge", "True").lower() in ["true", "1", "yes"]
project_dir = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


def _get_runtime_sid(runtime: Runtime) -> str:
    logger.debug("\nruntime.sid: %s", runtime.sid)
    return runtime.sid


def _get_host_folder(runtime: Runtime) -> str:
    return str(runtime.workspace_root)


def _remove_folder(folder: str) -> bool:
    success = False
    if folder and os.path.isdir(folder):
        try:
            os.rmdir(folder)
            success = True
        except OSError:
            try:
                shutil.rmtree(folder)
                success = True
            except OSError:
                pass
        logger.debug(f"\nCleanup: `{folder}`: " + ("[OK]" if success else "[FAILED]"))
    return success


def _close_test_runtime(runtime: Runtime) -> None:
    try:
        runtime.close()
    except TypeError:
        # Some runtimes may accept additional args; call without them
        runtime.close()
    time.sleep(1)


def _reset_cwd() -> None:
    global project_dir
    try:
        os.chdir(project_dir)
        logger.info("Changed back to project directory `%s", project_dir)
    except Exception as e:
        logger.error("Failed to change back to project directory: %s", e)


@pytest.fixture(autouse=True)
def print_method_name(request):
    print(
        "\n\n########################################################################"
    )
    print(f"Running test: {request.node.name}")
    print(
        "########################################################################\n\n"
    )


@pytest.fixture
def temp_dir(tmp_path_factory: TempPathFactory, request) -> str:
    """Creates a unique temporary directory.

    Upon finalization, the temporary directory and its content is removed.
    The cleanup function is also called upon KeyboardInterrupt.

    Parameters:
    - tmp_path_factory (TempPathFactory): A TempPathFactory class

    Returns:
    - str: The temporary directory path that was created
    """
    temp_dir = tmp_path_factory.mktemp(
        f"rt_{random.randint(100000, 999999)}", numbered=False
    )
    logger.info("\n*** %s\n>> temp folder: %s\n", request.node.name, temp_dir)
    os.chmod(temp_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

    def cleanup():
        global project_dir
        os.chdir(project_dir)
        _remove_folder(temp_dir)

    request.addfinalizer(cleanup)
    return str(temp_dir)


def get_runtime_classes() -> list[type[Runtime]]:
    return [LocalRuntime]


def get_run_as_Forge() -> list[bool]:
    print(
        "\n\n########################################################################"
    )
    print("USER: " + "forge" if RUN_AS_Forge else "root")
    print(
        "########################################################################\n\n"
    )
    return [RUN_AS_Forge]


@pytest.fixture(scope="module")
def runtime_setup_module():
    _reset_cwd()
    yield
    _reset_cwd()


@pytest.fixture(scope="session")
def runtime_setup_session():
    _reset_cwd()
    yield
    _reset_cwd()


@pytest.fixture(scope="module", params=get_runtime_classes())
def runtime_cls(request):
    time.sleep(1)
    return request.param


@pytest.fixture(scope="module", params=get_run_as_Forge())
def run_as_Forge(request):
    time.sleep(1)
    return request.param


def _load_runtime(
    temp_dir,
    runtime_cls,
    run_as_Forge: bool = True,
    enable_auto_lint: bool = False,
    browsergym_eval_env: str | None = None,
    use_workspace: bool | None = None,
    force_rebuild_runtime: bool = False,
    runtime_startup_env_vars: dict[str, str] | None = None,
    override_mcp_config: MCPConfig | None = None,
    enable_browser: bool = False,
) -> tuple[Runtime, ForgeConfig]:
    sid = f"rt_{random.randint(100000, 999999)}"
    plugins = [AgentSkillsRequirement()]
    config = load_FORGE_config()
    config.run_as_Forge = run_as_Forge
    config.enable_browser = enable_browser
    config.sandbox.force_rebuild_runtime = force_rebuild_runtime
    config.sandbox.keep_runtime_alive = False
    
    workspace_base = temp_dir
    
    print("\nPaths used:")
    print(f"use_host_network: {config.sandbox.use_host_network}")
    print(f"workspace_base: {workspace_base}")
    
    config.sandbox.browsergym_eval_env = browsergym_eval_env
    config.sandbox.enable_auto_lint = enable_auto_lint
    if runtime_startup_env_vars is not None:
        config.sandbox.runtime_startup_env_vars = runtime_startup_env_vars
    
    if override_mcp_config is not None:
        config.mcp = override_mcp_config
    
    file_store = get_file_store(
        file_store_type=config.file_store,
        file_store_path=config.file_store_path,
        file_store_web_hook_url=config.file_store_web_hook_url,
        file_store_web_hook_headers=config.file_store_web_hook_headers,
        file_store_web_hook_batch=config.file_store_web_hook_batch,
    )
    event_stream = EventStream(sid, file_store)
    llm_registry = LLMRegistry(config=ForgeConfig())
    runtime = runtime_cls(
        config=config,
        event_stream=event_stream,
        llm_registry=llm_registry,
        sid=sid,
        plugins=plugins,
        workspace_base=workspace_base,
    )
    call_async_from_sync(runtime.connect)
    time.sleep(2)
    return (runtime, runtime.config)


__all__ = ["_load_runtime", "_get_host_folder", "_remove_folder"]
