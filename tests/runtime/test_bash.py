"""Bash-related tests for the DockerRuntime, which connects to the ActionExecutor running in the sandbox."""

import os
import sys
import time
from pathlib import Path
import pytest
from conftest import _close_test_runtime, _load_runtime
from forge.core.logger import forge_logger as logger
from forge.events.action import CmdRunAction
from forge.events.observation import CmdOutputObservation, ErrorObservation
from forge.runtime.impl.cli.cli_runtime import CLIRuntime
from forge.runtime.impl.local.local_runtime import LocalRuntime
from forge.runtime.utils.bash_constants import TIMEOUT_MESSAGE_TEMPLATE


def get_timeout_suffix(timeout_seconds):
    """Helper function to generate the expected timeout suffix."""
    return f"[The command timed out after {timeout_seconds} seconds. {TIMEOUT_MESSAGE_TEMPLATE}]"


def is_windows():
    return sys.platform == "win32"


def _run_cmd_action(runtime, custom_command: str):
    action = CmdRunAction(command=custom_command)
    logger.info(action, extra={"msg_type": "ACTION"})
    obs = runtime.run_action(action)
    assert isinstance(obs, (CmdOutputObservation, ErrorObservation))
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    return obs


def get_platform_command(linux_cmd, windows_cmd):
    return windows_cmd if is_windows() else linux_cmd


def _test_http_server_startup(runtime, runtime_cls):
    """Test starting HTTP server and verify timeout behavior."""
    action = CmdRunAction(command="python -u -m http.server 8081")
    action.set_hard_timeout(1)
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, CmdOutputObservation)
    assert obs.exit_code == -1
    assert "Serving HTTP on" in obs.content
    if runtime_cls == CLIRuntime:
        assert "[The command timed out after 1.0 seconds.]" in obs.metadata.suffix
    else:
        assert get_timeout_suffix(1.0) in obs.metadata.suffix
    return obs


def _test_interrupt_handling(runtime, runtime_cls, config):
    """Test interrupt handling for different runtime types."""
    action = CmdRunAction(command="C-c", is_input=True)
    action.set_hard_timeout(30)
    obs_interrupt = runtime.run_action(action)
    logger.info(obs_interrupt, extra={"msg_type": "OBSERVATION"})

    if runtime_cls == CLIRuntime:
        assert isinstance(obs_interrupt, ErrorObservation)
        assert (
            "CLIRuntime does not support interactive input from the agent (e.g., 'C-c'). The command 'C-c' was not sent to any process."
            in obs_interrupt.content
        )
        assert obs_interrupt.error_id == "AGENT_ERROR$BAD_ACTION"
    else:
        assert isinstance(obs_interrupt, CmdOutputObservation)
        assert obs_interrupt.exit_code == 0
        if not is_windows():
            assert "Keyboard interrupt received, exiting." in obs_interrupt.content
            assert (
                config.workspace_mount_path_in_sandbox
                in obs_interrupt.metadata.working_dir
            )
    return obs_interrupt


def _test_post_interrupt_verification(runtime, runtime_cls, config):
    """Test that system is working after interrupt."""
    action = CmdRunAction(command="ls")
    action.set_hard_timeout(3)
    obs = runtime.run_action(action)
    logger.info(obs, extra={"msg_type": "OBSERVATION"})
    assert isinstance(obs, CmdOutputObservation)
    assert obs.exit_code == 0
    assert "Keyboard interrupt received, exiting." not in obs.content
    if runtime_cls == CLIRuntime:
        assert obs.metadata.working_dir == config.workspace_base
    else:
        assert config.workspace_mount_path_in_sandbox in obs.metadata.working_dir
    return obs


def test_bash_server(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        # Test HTTP server startup
        _test_http_server_startup(runtime, runtime_cls)

        # Test interrupt handling
        _test_interrupt_handling(runtime, runtime_cls, config)

        # Test post-interrupt verification
        _test_post_interrupt_verification(runtime, runtime_cls, config)

        # Test server restart
        _test_http_server_startup(runtime, runtime_cls)
    finally:
        _close_test_runtime(runtime)


def test_bash_background_server(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    server_port = 8081
    try:
        action = CmdRunAction(f"python3 -m http.server {server_port} &")
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert isinstance(obs, CmdOutputObservation)
        assert obs.exit_code == 0
        if runtime_cls == CLIRuntime:
            time.sleep(1)
            curl_action = CmdRunAction(
                f"curl --fail --connect-timeout 1 http://localhost:{server_port}"
            )
            curl_obs = runtime.run_action(curl_action)
            logger.info(curl_obs, extra={"msg_type": "OBSERVATION"})
            assert isinstance(curl_obs, CmdOutputObservation)
            assert curl_obs.exit_code != 0
            kill_action = CmdRunAction('pkill -f "http.server"')
        else:
            time.sleep(1)
            if is_windows():
                curl_action = CmdRunAction(
                    f"Invoke-WebRequest -Uri http://localhost:{server_port} -UseBasicParsing | Select-Object -ExpandProperty Content"
                )
            else:
                curl_action = CmdRunAction(f"curl http://localhost:{server_port}")
            curl_obs = runtime.run_action(curl_action)
            logger.info(curl_obs, extra={"msg_type": "OBSERVATION"})
            assert isinstance(curl_obs, CmdOutputObservation)
            assert curl_obs.exit_code == 0
            assert "Directory listing for" in curl_obs.content
            if is_windows():
                kill_action = CmdRunAction("Get-Job | Stop-Job")
            else:
                kill_action = CmdRunAction('pkill -f "http.server"')
        kill_obs = runtime.run_action(kill_action)
        logger.info(kill_obs, extra={"msg_type": "OBSERVATION"})
        assert isinstance(kill_obs, CmdOutputObservation)
        assert kill_obs.exit_code == 0
    finally:
        _close_test_runtime(runtime)


def test_multiline_commands(temp_dir, runtime_cls):
    runtime, config = _load_runtime(temp_dir, runtime_cls)
    try:
        if is_windows():
            obs = _run_cmd_action(runtime, 'Write-Output `\n "foo"')
            assert obs.exit_code == 0, "The exit code should be 0."
            assert "foo" in obs.content
            obs = _run_cmd_action(runtime, 'Write-Output "hello`nworld"')
            assert obs.exit_code == 0, "The exit code should be 0."
            assert "hello\nworld" in obs.content
            obs = _run_cmd_action(runtime, 'Write-Output "a`n`n`nz"')
        else:
            obs = _run_cmd_action(runtime, 'echo \\\n -e "foo"')
            assert obs.exit_code == 0, "The exit code should be 0."
            assert "foo" in obs.content
            obs = _run_cmd_action(runtime, 'echo -e "hello\nworld"')
            assert obs.exit_code == 0, "The exit code should be 0."
            assert "hello\nworld" in obs.content
            obs = _run_cmd_action(runtime, 'echo -e "a\\n\\n\\nz"')
        assert obs.exit_code == 0, "The exit code should be 0."
        assert "\n\n\n" in obs.content
    finally:
        _close_test_runtime(runtime)


@pytest.mark.skipif(
    is_windows(), reason="Test relies on Linux bash-specific complex commands"
)
def test_complex_commands(temp_dir, runtime_cls, run_as_Forge):
    cmd = 'count=0; tries=0; while [ $count -lt 3 ]; do result=$(echo "Heads"); tries=$((tries+1)); echo "Flip $tries: $result"; if [ "$result" = "Heads" ]; then count=$((count+1)); else count=0; fi; done; echo "Got 3 heads in a row after $tries flips!";'
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        obs = _run_cmd_action(runtime, cmd)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert obs.exit_code == 0, "The exit code should be 0."
        assert "Got 3 heads in a row after 3 flips!" in obs.content
    finally:
        _close_test_runtime(runtime)


def test_no_ps2_in_output(temp_dir, runtime_cls, run_as_Forge):
    """Test that the PS2 sign is not added to the output of a multiline command."""
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        if is_windows():
            obs = _run_cmd_action(runtime, 'Write-Output "hello`nworld"')
        else:
            obs = _run_cmd_action(runtime, 'echo -e "hello\nworld"')
        assert obs.exit_code == 0, "The exit code should be 0."
        assert "hello\nworld" in obs.content
        assert ">" not in obs.content
    finally:
        _close_test_runtime(runtime)


@pytest.mark.skipif(
    is_windows(), reason="Test uses Linux-specific bash loops and sed commands"
)
def test_multiline_command_loop(temp_dir, runtime_cls):
    init_cmd = 'mkdir -p _modules && for month in {01..04}; do\n    for day in {01..05}; do\n        touch "_modules/2024-${month}-${day}-sample.md"\n    done\ndone && echo "created files"\n'
    follow_up_cmd = 'for file in _modules/*.md; do\n    new_date=$(echo $file | sed -E \'s/2024-(01|02|03|04)-/2024-/;s/2024-01/2024-08/;s/2024-02/2024-09/;s/2024-03/2024-10/;s/2024-04/2024-11/\')\n    mv "$file" "$new_date"\ndone && echo "success"\n'
    runtime, config = _load_runtime(temp_dir, runtime_cls)
    try:
        obs = _run_cmd_action(runtime, init_cmd)
        assert obs.exit_code == 0, "The exit code should be 0."
        assert "created files" in obs.content
        obs = _run_cmd_action(runtime, follow_up_cmd)
        assert obs.exit_code == 0, "The exit code should be 0."
        assert "success" in obs.content
    finally:
        _close_test_runtime(runtime)


@pytest.mark.skipif(
    os.getenv("TEST_RUNTIME") == "cli",
    reason="CLIRuntime uses bash -c which handles newline-separated commands. This test expects rejection. See test_cliruntime_multiple_newline_commands.",
)
def test_multiple_multiline_commands(temp_dir, runtime_cls, run_as_Forge):
    if is_windows():
        cmds = [
            "Get-ChildItem",
            'Write-Output "hello`nworld"',
            'Write-Output "hello it\'s me"',
            "Write-Output `\n    ('hello ' + `\n    'world')",
            "Write-Output 'hello\nworld\nare\nyou\nthere?'",
            "Write-Output 'hello\nworld\nare\nyou\n\nthere?'",
            "Write-Output 'hello\nworld \"'",
        ]
    else:
        cmds = [
            "ls -l",
            'echo -e "hello\nworld"',
            'echo -e "hello it\'s me"',
            "echo \\\n    -e 'hello' \\\n    world",
            "echo -e 'hello\\nworld\\nare\\nyou\\nthere?'",
            "echo -e 'hello\nworld\nare\nyou\n\nthere?'",
            "echo -e 'hello\nworld \"'",
        ]
    joined_cmds = "\n".join(cmds)
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        obs = _run_cmd_action(runtime, joined_cmds)
        assert isinstance(obs, ErrorObservation)
        assert "Cannot execute multiple commands at once" in obs.content
        results = []
        for cmd in cmds:
            obs = _run_cmd_action(runtime, cmd)
            assert isinstance(obs, CmdOutputObservation)
            assert obs.exit_code == 0
            results.append(obs.content)
        if not is_windows():
            assert "total 0" in results[0]
        assert "hello\nworld" in results[1]
        assert "hello it's me" in results[2]
        assert "hello world" in results[3]
        assert "hello\nworld\nare\nyou\nthere?" in results[4]
        assert "hello\nworld\nare\nyou\n\nthere?" in results[5]
        assert 'hello\nworld "' in results[6]
    finally:
        _close_test_runtime(runtime)


def test_cliruntime_multiple_newline_commands(temp_dir, run_as_Forge):
    runtime_cls = CLIRuntime
    if is_windows():
        pytest.skip(
            "CLIRuntime newline command test primarily for non-Windows bash behavior"
        )
    else:
        cmds = ['echo "hello"', 'echo -e "hello\nworld"', 'echo -e "hello it\'s me"']
        expected_outputs = ["hello", "hello\nworld", "hello it's me"]
    joined_cmds = "\n".join(cmds)
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        obs = _run_cmd_action(runtime, joined_cmds)
        assert isinstance(obs, CmdOutputObservation)
        assert obs.exit_code == 0
        for expected_part in expected_outputs:
            assert expected_part in obs.content
    finally:
        _close_test_runtime(runtime)


def _test_windows_commands(runtime, config):
    """Test Windows PowerShell commands."""
    obs = _run_cmd_action(
        runtime, f"Get-ChildItem -Path {config.workspace_mount_path_in_sandbox}"
    )
    assert obs.exit_code == 0

    obs = _run_cmd_action(runtime, "Get-ChildItem")
    assert obs.exit_code == 0

    obs = _run_cmd_action(runtime, "New-Item -ItemType Directory -Path test")
    assert obs.exit_code == 0

    obs = _run_cmd_action(runtime, "Get-ChildItem")
    assert obs.exit_code == 0
    assert "test" in obs.content

    obs = _run_cmd_action(runtime, "New-Item -ItemType File -Path test/foo.txt")
    assert obs.exit_code == 0

    obs = _run_cmd_action(runtime, "Get-ChildItem test")
    assert obs.exit_code == 0
    assert "foo.txt" in obs.content

    _run_cmd_action(runtime, "Remove-Item -Recurse -Force test")


def _test_unix_commands(runtime, config, runtime_cls, run_as_Forge):
    """Test Unix/Linux commands."""
    obs = _run_cmd_action(runtime, f"ls -l {config.workspace_mount_path_in_sandbox}")
    assert obs.exit_code == 0

    obs = _run_cmd_action(runtime, "ls -l")
    assert obs.exit_code == 0
    assert "total 0" in obs.content

    obs = _run_cmd_action(runtime, "mkdir test")
    assert obs.exit_code == 0

    obs = _run_cmd_action(runtime, "ls -l")
    assert obs.exit_code == 0

    # Check user context based on runtime type
    if run_as_Forge and runtime_cls != CLIRuntime and (runtime_cls != LocalRuntime):
        assert "forge" in obs.content
    elif runtime_cls not in [LocalRuntime, CLIRuntime]:
        assert "root" in obs.content

    assert "test" in obs.content

    obs = _run_cmd_action(runtime, "touch test/foo.txt")
    assert obs.exit_code == 0

    obs = _run_cmd_action(runtime, "ls -l test")
    assert obs.exit_code == 0
    assert "foo.txt" in obs.content

    _run_cmd_action(runtime, "rm -rf test")


def test_cmd_run(temp_dir, runtime_cls, run_as_Forge):
    """Test command execution in the runtime environment."""
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        if is_windows():
            _test_windows_commands(runtime, config)
        else:
            _test_unix_commands(runtime, config, runtime_cls, run_as_Forge)

        # Final assertion
        obs = _run_cmd_action(runtime, "ls -l" if not is_windows() else "Get-ChildItem")
        assert obs.exit_code == 0
    finally:
        _close_test_runtime(runtime)


@pytest.mark.skipif(
    sys.platform != "win32" and os.getenv("TEST_RUNTIME") == "cli",
    reason="CLIRuntime runs as the host user, so ~ is the host home. This test assumes a sandboxed user.",
)
def test_run_as_user_correct_home_dir(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        if is_windows():
            obs = _run_cmd_action(runtime, "cd $HOME && Get-Location")
            assert obs.exit_code == 0
            if runtime_cls == LocalRuntime:
                assert (
                    os.getenv("USERPROFILE") in obs.content
                    or os.getenv("HOME") in obs.content
                )
        else:
            obs = _run_cmd_action(runtime, "cd ~ && pwd")
            assert obs.exit_code == 0
            if runtime_cls == LocalRuntime:
                assert os.getenv("HOME") in obs.content
            elif run_as_Forge:
                assert "/home/Forge" in obs.content
            else:
                assert "/root" in obs.content
    finally:
        _close_test_runtime(runtime)


def test_multi_cmd_run_in_single_line(temp_dir, runtime_cls):
    runtime, config = _load_runtime(temp_dir, runtime_cls)
    try:
        if is_windows():
            obs = _run_cmd_action(runtime, "Get-Location && Get-ChildItem")
            assert obs.exit_code == 0
            assert config.workspace_mount_path_in_sandbox in obs.content
        else:
            obs = _run_cmd_action(runtime, "pwd && ls -l")
            assert obs.exit_code == 0
            assert config.workspace_mount_path_in_sandbox in obs.content
            assert "total 0" in obs.content
    finally:
        _close_test_runtime(runtime)


def test_stateful_cmd(temp_dir, runtime_cls):
    runtime, config = _load_runtime(temp_dir, runtime_cls)
    try:
        if is_windows():
            obs = _run_cmd_action(
                runtime, "New-Item -ItemType Directory -Path test -Force"
            )
            assert obs.exit_code == 0, "The exit code should be 0."
            obs = _run_cmd_action(runtime, "Set-Location test")
            assert obs.exit_code == 0, "The exit code should be 0."
            obs = _run_cmd_action(runtime, "Get-Location")
            assert obs.exit_code == 0, "The exit code should be 0."
            norm_path = config.workspace_mount_path_in_sandbox.replace(
                "\\", "/"
            ).replace("//", "/")
            test_path = f"{norm_path}/test".replace("//", "/")
            assert test_path in obs.content.replace("\\", "/")
        else:
            obs = _run_cmd_action(runtime, "mkdir -p test")
            assert obs.exit_code == 0, "The exit code should be 0."
            if runtime_cls == CLIRuntime:
                obs = _run_cmd_action(runtime, "cd test && pwd")
            else:
                obs = _run_cmd_action(runtime, "cd test")
                assert obs.exit_code == 0, "The exit code should be 0 for cd test."
                obs = _run_cmd_action(runtime, "pwd")
            assert obs.exit_code == 0, (
                "The exit code for the pwd command (or combined command) should be 0."
            )
            assert (
                f"{config.workspace_mount_path_in_sandbox}/test" in obs.content.strip()
            )
    finally:
        _close_test_runtime(runtime)


def test_failed_cmd(temp_dir, runtime_cls):
    runtime, config = _load_runtime(temp_dir, runtime_cls)
    try:
        obs = _run_cmd_action(runtime, "non_existing_command")
        assert obs.exit_code != 0, "The exit code should not be 0 for a failed command."
    finally:
        _close_test_runtime(runtime)


def _create_test_file(host_temp_dir):
    with open(os.path.join(host_temp_dir, "test_file.txt"), "w") as f:
        f.write("Hello, World!")


def test_copy_single_file(temp_dir, runtime_cls):
    runtime, config = _load_runtime(temp_dir, runtime_cls)
    try:
        sandbox_dir = config.workspace_mount_path_in_sandbox
        sandbox_file = os.path.join(sandbox_dir, "test_file.txt")
        _create_test_file(temp_dir)
        runtime.copy_to(os.path.join(temp_dir, "test_file.txt"), sandbox_dir)
        if is_windows():
            obs = _run_cmd_action(runtime, f"Get-ChildItem -Path {sandbox_dir}")
            assert obs.exit_code == 0
            assert "test_file.txt" in obs.content
            obs = _run_cmd_action(runtime, f"Get-Content {sandbox_file}")
        else:
            obs = _run_cmd_action(runtime, f"ls -alh {sandbox_dir}")
            assert obs.exit_code == 0
            assert "test_file.txt" in obs.content
            obs = _run_cmd_action(runtime, f"cat {sandbox_file}")
        assert obs.exit_code == 0
        assert "Hello, World!" in obs.content
    finally:
        _close_test_runtime(runtime)


def _create_host_test_dir_with_files(test_dir):
    logger.debug("creating `%s`", test_dir)
    if not os.path.isdir(test_dir):
        os.makedirs(test_dir, exist_ok=True)
    logger.debug("creating test files in `test_dir`")
    with open(os.path.join(test_dir, "file1.txt"), "w") as f:
        f.write("File 1 content")
    with open(os.path.join(test_dir, "file2.txt"), "w") as f:
        f.write("File 2 content")


def test_copy_directory_recursively(temp_dir, runtime_cls):
    """Test recursive directory copying functionality."""
    runtime, config = _load_runtime(temp_dir, runtime_cls)
    sandbox_dir = config.workspace_mount_path_in_sandbox

    try:
        # Setup test directory
        temp_dir_copy = os.path.join(temp_dir, "test_dir")
        _create_host_test_dir_with_files(temp_dir_copy)

        # Copy directory recursively
        runtime.copy_to(temp_dir_copy, sandbox_dir, recursive=True)

        # Verify directory structure
        _verify_directory_structure(runtime, sandbox_dir)

        # Verify file contents
        _verify_file_contents(runtime, sandbox_dir)

    finally:
        _close_test_runtime(runtime)


def _verify_directory_structure(runtime, sandbox_dir):
    """Verify the directory structure after copying."""
    if is_windows():
        _verify_windows_directory_structure(runtime, sandbox_dir)
    else:
        _verify_unix_directory_structure(runtime, sandbox_dir)


def _verify_windows_directory_structure(runtime, sandbox_dir):
    """Verify directory structure on Windows."""
    # Check root directory
    obs = _run_cmd_action(runtime, f"Get-ChildItem -Path {sandbox_dir}")
    assert obs.exit_code == 0
    assert "test_dir" in obs.content
    assert "file1.txt" not in obs.content
    assert "file2.txt" not in obs.content

    # Check subdirectory
    obs = _run_cmd_action(runtime, f"Get-ChildItem -Path {sandbox_dir}/test_dir")
    assert obs.exit_code == 0
    assert "file1.txt" in obs.content
    assert "file2.txt" in obs.content


def _verify_unix_directory_structure(runtime, sandbox_dir):
    """Verify directory structure on Unix-like systems."""
    # Check root directory
    obs = _run_cmd_action(runtime, f"ls -alh {sandbox_dir}")
    assert obs.exit_code == 0
    assert "test_dir" in obs.content
    assert "file1.txt" not in obs.content
    assert "file2.txt" not in obs.content

    # Check subdirectory
    obs = _run_cmd_action(runtime, f"ls -alh {sandbox_dir}/test_dir")
    assert obs.exit_code == 0
    assert "file1.txt" in obs.content
    assert "file2.txt" in obs.content


def _verify_file_contents(runtime, sandbox_dir):
    """Verify the contents of copied files."""
    if is_windows():
        obs = _run_cmd_action(runtime, f"Get-Content {sandbox_dir}/test_dir/file1.txt")
    else:
        obs = _run_cmd_action(runtime, f"cat {sandbox_dir}/test_dir/file1.txt")

    assert obs.exit_code == 0
    assert "File 1 content" in obs.content


def test_copy_to_non_existent_directory(temp_dir, runtime_cls):
    runtime, config = _load_runtime(temp_dir, runtime_cls)
    try:
        sandbox_dir = config.workspace_mount_path_in_sandbox
        _create_test_file(temp_dir)
        runtime.copy_to(
            os.path.join(temp_dir, "test_file.txt"), f"{sandbox_dir}/new_dir"
        )
        obs = _run_cmd_action(runtime, f"cat {sandbox_dir}/new_dir/test_file.txt")
        assert obs.exit_code == 0
        assert "Hello, World!" in obs.content
    finally:
        _close_test_runtime(runtime)


def _verify_file_not_exists(runtime, sandbox_dir, is_windows_platform):
    """Verify that test_file.txt does not exist in sandbox directory."""
    if is_windows_platform:
        cmd = f"Get-ChildItem -Path {sandbox_dir}"
    else:
        cmd = f"ls -alh {sandbox_dir}"

    obs = _run_cmd_action(runtime, cmd)
    assert obs.exit_code == 0
    assert "test_file.txt" not in obs.content


def _create_empty_file(runtime, sandbox_file, is_windows_platform):
    """Create an empty test file in the sandbox."""
    if is_windows_platform:
        cmd = f"New-Item -ItemType File -Path {sandbox_file} -Force"
    else:
        cmd = f"touch {sandbox_file}"

    obs = _run_cmd_action(runtime, cmd)
    assert obs.exit_code == 0


def _verify_file_exists(runtime, sandbox_dir, is_windows_platform):
    """Verify that test_file.txt exists in sandbox directory."""
    if is_windows_platform:
        cmd = f"Get-ChildItem -Path {sandbox_dir}"
    else:
        cmd = f"ls -alh {sandbox_dir}"

    obs = _run_cmd_action(runtime, cmd)
    assert obs.exit_code == 0
    assert "test_file.txt" in obs.content


def _verify_file_is_empty(runtime, sandbox_file, is_windows_platform):
    """Verify that the test file is empty."""
    if is_windows_platform:
        cmd = f"Get-Content {sandbox_file}"
    else:
        cmd = f"cat {sandbox_file}"

    obs = _run_cmd_action(runtime, cmd)
    assert obs.exit_code == 0
    assert obs.content.strip() == ""
    assert "Hello, World!" not in obs.content


def _copy_test_file_and_verify(runtime, temp_dir, sandbox_file, is_windows_platform):
    """Copy test file and verify its content."""
    _create_test_file(temp_dir)
    runtime.copy_to(
        os.path.join(temp_dir, "test_file.txt"), os.path.dirname(sandbox_file)
    )

    if is_windows_platform:
        cmd = f"Get-Content {sandbox_file}"
    else:
        cmd = f"cat {sandbox_file}"

    obs = _run_cmd_action(runtime, cmd)
    assert obs.exit_code == 0
    assert "Hello, World!" in obs.content
    return obs


def test_overwrite_existing_file(temp_dir, runtime_cls):
    runtime, config = _load_runtime(temp_dir, runtime_cls)
    try:
        sandbox_dir = config.workspace_mount_path_in_sandbox
        sandbox_file = os.path.join(sandbox_dir, "test_file.txt")
        is_windows_platform = is_windows()

        # Verify file doesn't exist initially
        _verify_file_not_exists(runtime, sandbox_dir, is_windows_platform)

        # Create empty file
        _create_empty_file(runtime, sandbox_file, is_windows_platform)

        # Verify file exists
        _verify_file_exists(runtime, sandbox_dir, is_windows_platform)

        # Verify file is empty
        _verify_file_is_empty(runtime, sandbox_file, is_windows_platform)

        # Copy test file and verify content
        _copy_test_file_and_verify(runtime, temp_dir, sandbox_file, is_windows_platform)

    finally:
        _close_test_runtime(runtime)


def test_copy_non_existent_file(temp_dir, runtime_cls):
    runtime, config = _load_runtime(temp_dir, runtime_cls)
    try:
        sandbox_dir = config.workspace_mount_path_in_sandbox
        with pytest.raises(FileNotFoundError):
            runtime.copy_to(
                os.path.join(sandbox_dir, "non_existent_file.txt"),
                f"{sandbox_dir}/should_not_exist.txt",
            )
        obs = _run_cmd_action(runtime, f"ls {sandbox_dir}/should_not_exist.txt")
        assert obs.exit_code != 0
    finally:
        _close_test_runtime(runtime)


def test_copy_from_directory(temp_dir, runtime_cls):
    runtime, config = _load_runtime(temp_dir, runtime_cls)
    sandbox_dir = config.workspace_mount_path_in_sandbox
    try:
        temp_dir_copy = os.path.join(temp_dir, "test_dir")
        _create_host_test_dir_with_files(temp_dir_copy)
        runtime.copy_to(temp_dir_copy, sandbox_dir, recursive=True)
        path_to_copy_from = f"{sandbox_dir}/test_dir"
        result = runtime.copy_from(path=path_to_copy_from)
        assert isinstance(result, Path)
        if result.exists() and (not is_windows()):
            result.unlink()
    finally:
        _close_test_runtime(runtime)


@pytest.mark.skipif(
    is_windows(), reason="Test uses Linux-specific file permissions and sudo commands"
)
def _setup_git_permissions(runtime, runtime_cls):
    """Setup proper permissions for git operations."""
    if runtime_cls not in [LocalRuntime, CLIRuntime]:
        obs = _run_cmd_action(runtime, "sudo chown -R Forge:root .")
        assert obs.exit_code == 0
    return obs


def _verify_directory_permissions(runtime, runtime_cls):
    """Verify directory permissions are correct."""
    obs = _run_cmd_action(runtime, "ls -alh .")
    assert obs.exit_code == 0
    for line in obs.content.split("\n"):
        if runtime_cls in [LocalRuntime, CLIRuntime]:
            continue
        if " .." in line:
            assert "root" in line
            assert "forge" not in line
        elif " ." in line:
            assert "forge" in line
            assert "root" in line
    return obs


def _setup_git_repository(runtime, runtime_cls):
    """Initialize git repository and create test file."""
    obs = _run_cmd_action(runtime, "git init")
    assert obs.exit_code == 0
    obs = _run_cmd_action(runtime, 'echo "hello" > test_file.txt')
    assert obs.exit_code == 0
    return obs


def _configure_git_user(runtime, runtime_cls):
    """Configure git user for local and CLI runtimes."""
    if runtime_cls in [LocalRuntime, CLIRuntime]:
        logger.info("Setting git config author")
        obs = _run_cmd_action(
            runtime,
            'git config user.name "forge" && git config user.email "Forge@all-hands.dev"',
        )
        assert obs.exit_code == 0
        obs = _run_cmd_action(runtime, "git config --list")
        assert obs.exit_code == 0
        return obs
    return None


def _perform_git_operations(runtime):
    """Perform git add, diff, and commit operations."""
    obs = _run_cmd_action(runtime, "git add test_file.txt")
    assert obs.exit_code == 0
    obs = _run_cmd_action(runtime, "git diff --no-color --cached")
    assert obs.exit_code == 0
    assert "b/test_file.txt" in obs.content
    assert "+hello" in obs.content
    obs = _run_cmd_action(runtime, 'git commit -m "test commit"')
    assert obs.exit_code == 0
    return obs


def test_git_operation(temp_dir, runtime_cls):
    runtime, config = _load_runtime(
        temp_dir=temp_dir,
        use_workspace=False,
        runtime_cls=runtime_cls,
        run_as_Forge=True,
    )
    try:
        # Setup permissions
        _setup_git_permissions(runtime, runtime_cls)

        # Verify permissions
        _verify_directory_permissions(runtime, runtime_cls)

        # Setup git repository
        _setup_git_repository(runtime, runtime_cls)

        # Configure git user if needed
        _configure_git_user(runtime, runtime_cls)

        # Perform git operations
        _perform_git_operations(runtime)
    finally:
        _close_test_runtime(runtime)


def test_python_version(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        obs = runtime.run_action(CmdRunAction(command="python --version"))
        assert isinstance(obs, CmdOutputObservation), (
            "The observation should be a CmdOutputObservation."
        )
        assert obs.exit_code == 0, "The exit code should be 0."
        assert "Python 3" in obs.content, 'The output should contain "Python 3".'
    finally:
        _close_test_runtime(runtime)


def test_pwd_property(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        obs = _run_cmd_action(runtime, "mkdir -p random_dir")
        assert obs.exit_code == 0
        obs = _run_cmd_action(runtime, "cd random_dir && pwd")
        assert obs.exit_code == 0
        assert "random_dir" in obs.content
    finally:
        _close_test_runtime(runtime)


def test_basic_command(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        if is_windows():
            obs = _run_cmd_action(runtime, "Write-Output 'hello world'")
            assert "hello world" in obs.content
            assert obs.exit_code == 0
            obs = _run_cmd_action(runtime, "nonexistent_command")
            assert obs.exit_code != 0
            assert "not recognized" in obs.content or "command not found" in obs.content
            obs = _run_cmd_action(
                runtime, 'Write-Output "hello   world    with`nspecial  chars"'
            )
            assert "hello   world    with\nspecial  chars" in obs.content
            assert obs.exit_code == 0
            obs = _run_cmd_action(
                runtime,
                'Write-Output "first" && Write-Output "second" && Write-Output "third"',
            )
        else:
            obs = _run_cmd_action(runtime, "echo 'hello world'")
            assert "hello world" in obs.content
            assert obs.exit_code == 0
            obs = _run_cmd_action(runtime, "nonexistent_command")
            assert obs.exit_code == 127
            assert "nonexistent_command: command not found" in obs.content
            obs = _run_cmd_action(
                runtime, "echo 'hello   world    with\nspecial  chars'"
            )
            assert "hello   world    with\nspecial  chars" in obs.content
            assert obs.exit_code == 0
            obs = _run_cmd_action(
                runtime, 'echo "first" && echo "second" && echo "third"'
            )
        assert "first" in obs.content
        assert "second" in obs.content
        assert "third" in obs.content
        assert obs.exit_code == 0
    finally:
        _close_test_runtime(runtime)


@pytest.mark.skipif(
    is_windows(), reason="Powershell does not support interactive commands"
)
@pytest.mark.skipif(
    os.getenv("TEST_RUNTIME") == "cli",
    reason="CLIRuntime does not support interactive commands from the agent.",
)
def test_interactive_command(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(
        temp_dir,
        runtime_cls,
        run_as_Forge,
        runtime_startup_env_vars={"NO_CHANGE_TIMEOUT_SECONDS": "1"},
    )
    try:
        action = CmdRunAction('read -p "Enter name: " name && echo "Hello $name"')
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert "Enter name:" in obs.content
        assert "[The command has no new output after 1 seconds." in obs.metadata.suffix
        action = CmdRunAction("John", is_input=True)
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert "Hello John" in obs.content
        assert "[The command completed with exit code 0.]" in obs.metadata.suffix
        action = CmdRunAction("cat << EOF\nline 1\nline 2\nEOF")
        obs = runtime.run_action(action)
        assert "line 1\nline 2" in obs.content
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert "[The command completed with exit code 0.]" in obs.metadata.suffix
        assert obs.exit_code == 0
    finally:
        _close_test_runtime(runtime)


@pytest.mark.skipif(
    is_windows(),
    reason="Test relies on Linux-specific commands like seq and bash for loops",
)
def test_long_output(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        action = CmdRunAction('for i in $(seq 1 5000); do echo "Line $i"; done')
        action.set_hard_timeout(10)
        obs = runtime.run_action(action)
        assert obs.exit_code == 0
        assert "Line 1" in obs.content
        assert "Line 5000" in obs.content
    finally:
        _close_test_runtime(runtime)


@pytest.mark.skipif(
    is_windows(),
    reason="Test relies on Linux-specific commands like seq and bash for loops",
)
@pytest.mark.skipif(
    os.getenv("TEST_RUNTIME") == "cli",
    reason="CLIRuntime does not truncate command output.",
)
def test_long_output_exceed_history_limit(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        action = CmdRunAction('for i in $(seq 1 50000); do echo "Line $i"; done')
        action.set_hard_timeout(30)
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert obs.exit_code == 0
        assert "Previous command outputs are truncated" in obs.metadata.prefix
        assert "Line 40000" in obs.content
        assert "Line 50000" in obs.content
    finally:
        _close_test_runtime(runtime)


@pytest.mark.skipif(
    is_windows(), reason="Test uses Linux-specific temp directory and bash for loops"
)
def test_long_output_from_nested_directories(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        setup_cmd = 'mkdir -p /tmp/test_dir && cd /tmp/test_dir && for i in $(seq 1 100); do mkdir -p "folder_$i"; for j in $(seq 1 100); do touch "folder_$i/file_$j.txt"; done; done'
        setup_action = CmdRunAction(setup_cmd.strip())
        setup_action.set_hard_timeout(60)
        obs = runtime.run_action(setup_action)
        assert obs.exit_code == 0
        action = CmdRunAction("ls -R /tmp/test_dir")
        action.set_hard_timeout(60)
        obs = runtime.run_action(action)
        assert obs.exit_code == 0
        assert "folder_1" in obs.content
        assert "file_1.txt" in obs.content
        assert "folder_100" in obs.content
        assert "file_100.txt" in obs.content
    finally:
        _close_test_runtime(runtime)


@pytest.mark.skipif(
    is_windows(),
    reason="Test uses Linux-specific commands like find and grep with complex syntax",
)
def test_command_backslash(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        action = CmdRunAction(
            'mkdir -p /tmp/test_dir && echo "implemented_function" > /tmp/test_dir/file_1.txt'
        )
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert obs.exit_code == 0
        action = CmdRunAction(
            'find /tmp/test_dir -type f -exec grep -l "implemented_function" {} \\;'
        )
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert obs.exit_code == 0
        assert "/tmp/test_dir/file_1.txt" in obs.content  # nosec B108 - Safe: test assertion
    finally:
        _close_test_runtime(runtime)


@pytest.mark.skipif(
    is_windows(), reason="Test uses Linux-specific ps aux, awk, and grep commands"
)
@pytest.mark.skipif(
    os.getenv("TEST_RUNTIME") == "cli",
    reason="CLIRuntime does not support interactive commands from the agent.",
)
def test_stress_long_output_with_soft_and_hard_timeout(
    temp_dir, runtime_cls, run_as_Forge
):
    runtime, config = _load_runtime(
        temp_dir,
        runtime_cls,
        run_as_Forge,
        runtime_startup_env_vars={"NO_CHANGE_TIMEOUT_SECONDS": "1"},
        docker_runtime_kwargs={
            "cpu_period": 100000,
            "cpu_quota": 100000,
            "mem_limit": "4G",
        },
    )
    try:
        for i in range(10):
            start_time = time.time()
            mem_action = CmdRunAction(
                "ps aux | awk '{printf \"%8.1f KB  %s\\n\", $6, $0}' | sort -nr | grep \"/usr/bin/tmux\" | grep -v grep | awk '{print $1}'"
            )
            mem_obs = runtime.run_action(mem_action)
            assert mem_obs.exit_code == 0
            logger.info(
                "Tmux memory usage (iteration %s): %s KB", i, mem_obs.content.strip()
            )
            mem_action = CmdRunAction(
                'ps aux | awk \'{printf "%8.1f KB  %s\\n", $6, $0}\' | sort -nr | grep "action_execution_server" | grep "/Forge/poetry" | grep -v grep | awk \'{print $1}\''
            )
            mem_obs = runtime.run_action(mem_action)
            assert mem_obs.exit_code == 0
            logger.info(
                "Action execution server memory usage (iteration %s): %s KB",
                i,
                mem_obs.content.strip(),
            )
            action = CmdRunAction(
                'read -p "Do you want to continue? [Y/n] " answer; if [[ $answer == "Y" ]]; then echo "Proceeding with operation..."; echo "Operation completed successfully!"; else echo "Operation cancelled."; exit 1; fi'
            )
            obs = runtime.run_action(action)
            assert "Do you want to continue?" in obs.content
            assert obs.exit_code == -1
            action = CmdRunAction("Y", is_input=True)
            obs = runtime.run_action(action)
            assert "Proceeding with operation..." in obs.content
            assert "Operation completed successfully!" in obs.content
            assert obs.exit_code == 0
            assert "[The command completed with exit code 0.]" in obs.metadata.suffix
            action = CmdRunAction(
                f"""export i={i}; for j in $(seq 1 100); do echo "Line $j - Iteration $i - $(printf '%1000s' | tr " " "*")"; sleep 1; done"""
            )
            action.set_hard_timeout(2)
            obs = runtime.run_action(action)
            assert obs.exit_code == -1
            assert f"Line 1 - Iteration {i}" in obs.content
            obs = runtime.run_action(CmdRunAction("ls"))
            assert obs.exit_code == -1
            assert "The previous command is still running" in obs.metadata.suffix
            obs = runtime.run_action(CmdRunAction("C-c", is_input=True))
            assert obs.exit_code == 130
            obs = runtime.run_action(CmdRunAction("ls"))
            assert obs.exit_code == 0
            duration = time.time() - start_time
            logger.info("Completed iteration %s in %s seconds", i, duration)
    finally:
        _close_test_runtime(runtime)


@pytest.mark.skipif(
    os.getenv("TEST_RUNTIME") == "cli",
    reason="FIXME: CLIRuntime does not watch previously timed-out commands except for getting full output a short time after timeout.",
)
def test_command_output_continuation(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        if is_windows():
            action = CmdRunAction(
                "1..5 | ForEach-Object { Write-Output $_; Start-Sleep 3 }"
            )
        else:
            action = CmdRunAction("for i in {1..5}; do echo $i; sleep 3; done")
        action.set_hard_timeout(2.5)
        obs = runtime.run_action(action)
        assert obs.content.strip() == "1"
        assert obs.metadata.prefix == ""
        assert "[The command timed out after 2.5 seconds." in obs.metadata.suffix
        action = CmdRunAction("")
        action.set_hard_timeout(2.5)
        obs = runtime.run_action(action)
        assert "[Below is the output of the previous command.]" in obs.metadata.prefix
        assert obs.content.strip() == "2"
        assert "[The command timed out after 2.5 seconds." in obs.metadata.suffix
        for expected in ["3", "4", "5"]:
            action = CmdRunAction("")
            action.set_hard_timeout(2.5)
            obs = runtime.run_action(action)
            assert (
                "[Below is the output of the previous command.]" in obs.metadata.prefix
            )
            assert obs.content.strip() == expected
            assert "[The command timed out after 2.5 seconds." in obs.metadata.suffix
        action = CmdRunAction("")
        obs = runtime.run_action(action)
        assert "[The command completed with exit code 0.]" in obs.metadata.suffix
    finally:
        _close_test_runtime(runtime)


@pytest.mark.skipif(
    os.getenv("TEST_RUNTIME") == "cli",
    reason="FIXME: CLIRuntime does not implement empty command behavior.",
)
def test_long_running_command_follow_by_execute(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        if is_windows():
            action = CmdRunAction("1..3 | ForEach-Object { Write-Output $_; sleep 3 }")
        else:
            action = CmdRunAction("for i in {1..3}; do echo $i; sleep 3; done")
        action.set_hard_timeout(2.5)
        obs = runtime.run_action(action)
        assert "1" in obs.content
        assert obs.metadata.exit_code == -1
        assert "[The command timed out after 2.5 seconds." in obs.metadata.suffix
        assert obs.metadata.prefix == ""
        action = CmdRunAction("")
        action.set_hard_timeout(2.5)
        obs = runtime.run_action(action)
        assert "2" in obs.content
        assert obs.metadata.prefix == "[Below is the output of the previous command.]\n"
        assert "[The command timed out after 2.5 seconds." in obs.metadata.suffix
        assert obs.metadata.exit_code == -1
        action = CmdRunAction("sleep 15")
        action.set_hard_timeout(2.5)
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert "3" not in obs.content
        assert obs.metadata.prefix == "[Below is the output of the previous command.]\n"
        assert "The previous command is still running" in obs.metadata.suffix
        assert obs.metadata.exit_code == -1
        action = CmdRunAction("")
        obs = runtime.run_action(action)
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert "3" in obs.content
        assert "[The command completed with exit code 0.]" in obs.metadata.suffix
    finally:
        _close_test_runtime(runtime)


@pytest.mark.skipif(
    os.getenv("TEST_RUNTIME") == "cli",
    reason="FIXME: CLIRuntime does not implement empty command behavior.",
)
def test_empty_command_errors(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        obs = runtime.run_action(CmdRunAction(""))
        assert isinstance(obs, CmdOutputObservation)
        assert (
            "ERROR: No previous running command to retrieve logs from." in obs.content
        )
    finally:
        _close_test_runtime(runtime)


@pytest.mark.skipif(
    is_windows(), reason="Powershell does not support interactive commands"
)
@pytest.mark.skipif(
    os.getenv("TEST_RUNTIME") == "cli",
    reason="CLIRuntime does not support interactive commands from the agent.",
)
def test_python_interactive_input(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        python_script = "name = input('Enter your name: '); age = input('Enter your age: '); print(f'Hello {name}, you are {age} years old')"
        obs = runtime.run_action(CmdRunAction(f'python -c "{python_script}"'))
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert "Enter your name:" in obs.content
        assert obs.metadata.exit_code == -1
        obs = runtime.run_action(CmdRunAction("Alice", is_input=True))
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert "Enter your age:" in obs.content
        assert obs.metadata.exit_code == -1
        obs = runtime.run_action(CmdRunAction("25", is_input=True))
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert "Hello Alice, you are 25 years old" in obs.content
        assert obs.metadata.exit_code == 0
        assert "[The command completed with exit code 0.]" in obs.metadata.suffix
    finally:
        _close_test_runtime(runtime)


@pytest.mark.skipif(
    is_windows(), reason="Powershell does not support interactive commands"
)
@pytest.mark.skipif(
    os.getenv("TEST_RUNTIME") == "cli",
    reason="CLIRuntime does not support interactive commands from the agent.",
)
def test_python_interactive_input_without_set_input(
    temp_dir, runtime_cls, run_as_Forge
):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        python_script = "name = input('Enter your name: '); age = input('Enter your age: '); print(f'Hello {name}, you are {age} years old')"
        obs = runtime.run_action(CmdRunAction(f'python -c "{python_script}"'))
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert "Enter your name:" in obs.content
        assert obs.metadata.exit_code == -1
        obs = runtime.run_action(CmdRunAction("Alice", is_input=False))
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert "Enter your age:" not in obs.content
        assert (
            'Your command "Alice" is NOT executed. The previous command is still running'
            in obs.metadata.suffix
        )
        assert obs.metadata.exit_code == -1
        obs = runtime.run_action(CmdRunAction("Alice", is_input=True))
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert "Enter your age:" in obs.content
        assert obs.metadata.exit_code == -1
        obs = runtime.run_action(CmdRunAction("25", is_input=True))
        logger.info(obs, extra={"msg_type": "OBSERVATION"})
        assert "Hello Alice, you are 25 years old" in obs.content
        assert obs.metadata.exit_code == 0
        assert "[The command completed with exit code 0.]" in obs.metadata.suffix
    finally:
        _close_test_runtime(runtime)


def test_bash_remove_prefix(temp_dir, runtime_cls, run_as_Forge):
    runtime, config = _load_runtime(temp_dir, runtime_cls, run_as_Forge)
    try:
        action = CmdRunAction(
            "git init && git remote add origin https://github.com/All-Hands-AI/Forge"
        )
        obs = runtime.run_action(action)
        assert obs.metadata.exit_code == 0
        obs = runtime.run_action(CmdRunAction("git remote -v"))
        assert obs.metadata.exit_code == 0
        assert "https://github.com/All-Hands-AI/Forge" in obs.content
        assert "git remote -v" not in obs.content
    finally:
        _close_test_runtime(runtime)
