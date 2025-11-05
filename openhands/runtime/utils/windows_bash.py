"""This module provides a Windows-specific implementation for running commands in a PowerShell session using the pythonnet library to interact with the .NET.

It uses the PowerShell SDK directly. This aims to provide a more robust and integrated
way to manage PowerShell processes compared to using temporary script files.
"""

from __future__ import annotations

import sys

# CRITICAL: Platform check MUST be the very first thing after imports
# This prevents ANY execution of this module on non-Windows platforms
if sys.platform != "win32":
    class WindowsOnlyModuleError(Exception):
        def __init__(self):
            super().__init__(
                f"FATAL ERROR: This module (windows_bash.py) requires Windows platform, "
                f"but is running on {sys.platform}. This should never happen and indicates a "
                f"serious configuration issue. Please use the appropriate platform-specific runtime."
            )
    
    raise WindowsOnlyModuleError()

import os

import time
import traceback
from pathlib import Path
from threading import RLock
from typing import TYPE_CHECKING

import pythonnet

from openhands.core.logger import openhands_logger as logger
from openhands.events.observation import ErrorObservation
from openhands.events.observation.commands import (
    CmdOutputMetadata,
    CmdOutputObservation,
)
from openhands.runtime.utils.bash_constants import TIMEOUT_MESSAGE_TEMPLATE
from openhands.runtime.utils.windows_exceptions import DotNetMissingError
from openhands.utils.shutdown_listener import should_continue

if TYPE_CHECKING:
    import System

    from openhands.events.action import CmdRunAction

# Double-check platform before attempting .NET loading
if sys.platform != "win32":
    raise RuntimeError(f"Module execution reached .NET loading on {sys.platform} - this should never happen!")

try:
    pythonnet.load("coreclr")
    logger.info("Successfully called pythonnet.load('coreclr')")
    try:
        import clr

        logger.debug("Imported clr module from: %s", clr.__file__)
        clr.AddReference("System")
    except Exception as clr_sys_ex:
        error_msg = "Failed to import .NET components."
        details = str(clr_sys_ex)
        logger.error("%s Details: %s", error_msg, details)
        raise DotNetMissingError(error_msg, details) from clr_sys_ex
except Exception as coreclr_ex:
    error_msg = "Failed to load CoreCLR."
    details = str(coreclr_ex)
    logger.error("%s Details: %s", error_msg, details)
    raise DotNetMissingError(error_msg, details) from coreclr_ex
ps_sdk_path = None
try:
    pwsh7_path = (
        Path(os.environ.get("ProgramFiles", "C:\\Program Files"))
        / "PowerShell"
        / "7"
        / "System.Management.Automation.dll"
    )
    if pwsh7_path.exists():
        ps_sdk_path = str(pwsh7_path)
        clr.AddReference(ps_sdk_path)
        logger.info("Loaded PowerShell SDK (Core): %s", ps_sdk_path)
    else:
        winps_path = (
            Path(os.environ.get("SystemRoot", "C:\\Windows"))
            / "System32"
            / "WindowsPowerShell"
            / "v1.0"
            / "System.Management.Automation.dll"
        )
        if winps_path.exists():
            ps_sdk_path = str(winps_path)
            clr.AddReference(ps_sdk_path)
            logger.debug("Loaded PowerShell SDK (Desktop): %s", ps_sdk_path)
        else:
            clr.AddReference("System.Management.Automation")
            logger.info("Attempted to load PowerShell SDK by name (System.Management.Automation)")
    from System.Management.Automation import JobState, PowerShell
    from System.Management.Automation.Runspaces import RunspaceFactory, RunspaceState
except Exception as e:
    error_msg = "Failed to load PowerShell SDK components."
    # Provide more detailed diagnostics about what was searched
    searched_paths = []
    if ps_sdk_path:
        searched_paths.append(f"Found path: {ps_sdk_path}")
    else:
        # Report the paths that were checked
        pwsh7_path = (
            Path(os.environ.get("ProgramFiles", "C:\\Program Files"))
            / "PowerShell"
            / "7"
            / "System.Management.Automation.dll"
        )
        winps_path = (
            Path(os.environ.get("SystemRoot", "C:\\Windows"))
            / "System32"
            / "WindowsPowerShell"
            / "v1.0"
            / "System.Management.Automation.dll"
        )
        searched_paths.extend([
            f"PowerShell 7 path (checked): {pwsh7_path} - exists: {pwsh7_path.exists()}",
            f"Windows PowerShell path (checked): {winps_path} - exists: {winps_path.exists()}",
            "Attempted to load by assembly name: System.Management.Automation"
        ])
    
    details = f"{e!s}\nSearched paths:\n" + "\n".join(searched_paths)
    logger.error("%s Details: %s", error_msg, details)
    raise DotNetMissingError(error_msg, details) from e


class WindowsPowershellSession:
    """Manages a persistent PowerShell session using the .NET SDK via pythonnet.

    Allows executing commands within a single runspace, preserving state
    (variables, current directory) between calls.
    Handles basic timeout and captures output/error streams.
    """

    def __init__(
        self,
        work_dir: str,
        username: str | None = None,
        no_change_timeout_seconds: int = 30,
        max_memory_mb: int | None = None,
    ) -> None:
        """Initializes the PowerShell session.

        Args:
            work_dir: The starting working directory for the session.
            username: (Currently ignored) Username for execution. PowerShell SDK typically runs as the current user.
            no_change_timeout_seconds: Timeout in seconds if no output change is detected (currently NOT fully implemented).
            max_memory_mb: (Currently ignored) Maximum memory limit for the process.
        """
        self._closed = False
        self._initialized = False
        self.runspace = None
        if PowerShell is None:
            error_msg = "PowerShell SDK (System.Management.Automation.dll) could not be loaded."
            logger.error(error_msg)
            raise DotNetMissingError(error_msg)
        self.work_dir = os.path.abspath(work_dir)
        self.username = username
        self._cwd = self.work_dir
        self.NO_CHANGE_TIMEOUT_SECONDS = no_change_timeout_seconds
        self.max_memory_mb = max_memory_mb
        self.active_job = None
        self._job_lock = RLock()
        self._last_job_output = ""
        self._last_job_error: list[str] = []
        try:
            self.runspace = RunspaceFactory.CreateRunspace()
            self.runspace.Open()
            self._set_initial_cwd()
            self._initialized = True
            logger.info("PowerShell runspace created. Initial CWD set to: %s", self._cwd)
        except Exception as e:
            logger.error("Failed to create or open PowerShell runspace: %s", e)
            logger.error(traceback.format_exc())
            self.close()
            msg = f"Failed to initialize PowerShell runspace: {e}"
            raise RuntimeError(msg) from e

    def _set_initial_cwd(self) -> None:
        """Sets the initial working directory in the runspace."""
        ps = None
        try:
            ps = PowerShell.Create()
            ps.Runspace = self.runspace
            ps.AddScript(f'Set-Location -Path "{self._cwd}"').Invoke()
            if ps.Streams.Error:
                errors = "\n".join([str(err) for err in ps.Streams.Error])
                logger.warning("Error setting initial CWD to '%s': %s", self._cwd, errors)
                self._confirm_cwd()
            else:
                logger.debug("Successfully set initial runspace CWD to %s", self._cwd)
        except Exception as e:
            logger.error("Exception setting initial CWD: %s", e)
            logger.error(traceback.format_exc())
            self._confirm_cwd()
        finally:
            if ps:
                ps.Dispose()

    def _confirm_cwd(self) -> None:
        """Confirms the actual CWD in the runspace and updates self._cwd."""
        ps_confirm = None
        try:
            ps_confirm = PowerShell.Create()
            ps_confirm.Runspace = self.runspace
            ps_confirm.AddScript("Get-Location")
            results = ps_confirm.Invoke()
            if results and results.Count > 0 and hasattr(results[0], "Path"):
                actual_cwd = str(results[0].Path)
                if os.path.isdir(actual_cwd):
                    if actual_cwd != self._cwd:
                        logger.warning(
                            "Runspace CWD (%s) differs from expected (%s). Updating session CWD.",
                            actual_cwd,
                            self._cwd,
                        )
                        self._cwd = actual_cwd
                    else:
                        logger.debug("Confirmed runspace CWD is %s", self._cwd)
                else:
                    logger.error(
                        "Get-Location returned an invalid path: %s. Session CWD may be inaccurate.",
                        actual_cwd,
                    )
            elif ps_confirm.Streams.Error:
                errors = "\n".join([str(err) for err in ps_confirm.Streams.Error])
                logger.error("Error confirming runspace CWD: %s", errors)
            else:
                logger.error("Could not confirm runspace CWD (No result or error).")
        except Exception as e:
            logger.error("Exception confirming CWD: %s", e)
        finally:
            if ps_confirm:
                ps_confirm.Dispose()

    @property
    def cwd(self) -> str:
        """Gets the last known working directory of the session."""
        return self._cwd

    def _run_ps_command(self, script: str, log_output: bool = True) -> list[System.Management.Automation.PSObject]:
        """Helper to run a simple synchronous command in the runspace."""
        if log_output:
            logger.debug("Running PS command: '%s'", script)
        ps = None
        results = []
        try:
            ps = PowerShell.Create()
            ps.Runspace = self.runspace
            ps.AddScript(script)
            results = ps.Invoke()
        except Exception as e:
            logger.error("Exception running script: %s\n%s", script, e)
        finally:
            if ps:
                ps.Dispose()
        return results or []

    def _get_job_object(self, job_id: int | None) -> System.Management.Automation.Job | None:
        """Retrieves a job object by its ID."""
        script = f"Get-Job -Id {job_id}"
        results = self._run_ps_command(script, log_output=False)
        if results and len(results) > 0:
            potential_job_wrapper = results[0]
            try:
                underlying_job = potential_job_wrapper.BaseObject
                _ = underlying_job.Id
                _ = underlying_job.JobStateInfo.State
                return underlying_job
            except AttributeError:
                logger.warning("Retrieved object is not a valid job. ID: %s", job_id)
                return None
        return None

    def _receive_job_output(self, job: System.Management.Automation.Job, keep: bool = False) -> tuple[str, list[str]]:
        """Receives output and errors from a job."""
        if not job:
            return ("", [])

        output_parts = []
        error_parts = []

        # Read direct error stream
        self._read_direct_error_stream(job, error_parts)

        # Receive job output via PowerShell
        self._receive_job_via_powershell(job, keep, output_parts, error_parts)

        # Combine output
        final_combined_output = "\n".join(output_parts)
        return (final_combined_output, error_parts)

    def _read_direct_error_stream(self, job: System.Management.Automation.Job, error_parts: list[str]) -> None:
        """Read direct error stream from job object."""
        try:
            current_job_obj = self._get_job_object(job.Id)
            if current_job_obj and current_job_obj.Error:
                if error_records := current_job_obj.Error.ReadAll():
                    error_parts.extend([str(e) for e in error_records])
        except Exception as read_err:
            logger.error("Failed to read job error stream directly for Job %s: %s", job.Id, read_err)
            error_parts.append(f"[Direct Error Stream Read Exception: {read_err}]")

    def _receive_job_via_powershell(
        self, job: System.Management.Automation.Job, keep: bool, output_parts: list[str], error_parts: list[str],
    ) -> None:
        """Receive job output via PowerShell command."""
        keep_switch = "-Keep" if keep else ""
        script = f"Receive-Job -Job (Get-Job -Id {job.Id}) {keep_switch}"
        ps_receive = None

        try:
            ps_receive = self._create_powershell_instance()
            ps_receive.AddScript(script)

            # Invoke and collect results
            if results := ps_receive.Invoke():
                output_parts.extend([str(r) for r in results])

            # Collect errors
            self._collect_powershell_errors(ps_receive, job.Id, error_parts)

        except Exception as e:
            logger.error("Exception during Receive-Job for Job ID %s: %s", job.Id, e)
            error_parts.append(f"[Receive-Job Exception: {e}]")
        finally:
            if ps_receive:
                ps_receive.Dispose()

    def _create_powershell_instance(self):
        """Create and configure PowerShell instance."""
        ps_receive = PowerShell.Create()
        ps_receive.Runspace = self.runspace
        return ps_receive

    def _collect_powershell_errors(self, ps_receive, job_id: int, error_parts: list[str]) -> None:
        """Collect errors from PowerShell streams."""
        if ps_receive.Streams.Error:
            receive_job_errors = [str(e) for e in ps_receive.Streams.Error]
            logger.warning("Errors during Receive-Job for Job ID %s: %s", job_id, receive_job_errors)
            error_parts.extend(receive_job_errors)

    def _stop_active_job(self) -> CmdOutputObservation | ErrorObservation:
        """Stops the active job, collects final output, and cleans up."""
        with self._job_lock:
            job = self.active_job
            if not job:
                return ErrorObservation(content="ERROR: No previous running command to interact with.")
            job_id = job.Id
            logger.info("Attempting to stop job ID: %s via C-c.", job_id)
            stop_script = f"Stop-Job -Job (Get-Job -Id {job_id})"
            self._run_ps_command(stop_script)
            time.sleep(0.5)
            final_output, final_errors = self._receive_job_output(job, keep=False)
            combined_output = final_output
            combined_errors = final_errors
            final_job = self._get_job_object(job_id)
            final_state = final_job.JobStateInfo.State if final_job else JobState.Failed
            logger.info("Job %s final state after stop attempt: %s", job_id, final_state)
            remove_script = f"Remove-Job -Job (Get-Job -Id {job_id})"
            self._run_ps_command(remove_script)
            self.active_job = None
            output_builder = [combined_output] if combined_output else []
            if combined_errors:
                output_builder.append("\n[ERROR STREAM]")
                output_builder.extend(combined_errors)
            exit_code = 0 if final_state in [JobState.Stopped, JobState.Completed] else 1
            final_content = "\n".join(output_builder).strip()
            current_cwd = self._cwd
            python_safe_cwd = current_cwd.replace("\\\\", "\\\\\\\\")
            metadata = CmdOutputMetadata(exit_code=exit_code, working_dir=python_safe_cwd)
            metadata.suffix = f"\n[The command completed with exit code {exit_code}. CTRL+C was sent.]"
            return CmdOutputObservation(content=final_content, command="C-c", metadata=metadata)

    def _initialize_job_check(
        self,
        job_id: int,
        timeout_seconds: int,
    ) -> tuple[float, list[str], list[str], int, JobState, str, list[str]]:
        """Initialize job check variables and logging."""
        logger.info("Checking active job ID: %s for new output (timeout=%ss).", job_id, timeout_seconds)
        start_time = time.monotonic()
        accumulated_new_output_builder = []
        accumulated_new_errors = []
        exit_code = -1
        final_state = JobState.Running
        latest_cumulative_output = self._last_job_output
        latest_cumulative_errors = list(self._last_job_error)
        return (
            start_time,
            accumulated_new_output_builder,
            accumulated_new_errors,
            exit_code,
            final_state,
            latest_cumulative_output,
            latest_cumulative_errors,
        )

    def _check_shutdown_signal(self) -> bool:
        """Check if shutdown signal was received."""
        if not should_continue():
            logger.warning("Shutdown signal received during job check.")
            return True
        return False

    def _check_timeout(self, start_time: float, timeout_seconds: int) -> bool:
        """Check if job check has timed out."""
        elapsed_seconds = time.monotonic() - start_time
        if elapsed_seconds > timeout_seconds:
            logger.warning("Job check timed out after %ss.", timeout_seconds)
            return True
        return False

    def _handle_job_object_lost(self, job_id: int) -> tuple[bool, int, JobState]:
        """Handle case where job object is lost during check."""
        logger.error("Job %s object disappeared during check.", job_id)
        if self.active_job and self.active_job.Id == job_id:
            self.active_job = None
        return (True, 1, JobState.Failed)

    def _process_new_output(
        self,
        job_id: int,
        polled_output: str,
        latest_output: str,
        accumulated_output: list[str],
    ) -> None:
        """Process new output detected since last poll."""
        if polled_output != latest_output:
            if polled_output.startswith(latest_output):
                new_output_detected = polled_output[len(latest_output):]
            else:
                logger.warning("Job %s check: Cumulative output changed unexpectedly", job_id)
                new_output_detected = polled_output.removeprefix(self._last_job_output)
            if new_output_detected.strip():
                accumulated_output.append(new_output_detected.strip())

    def _process_new_errors(
        self,
        polled_errors: list[str],
        latest_errors: list[str],
        accumulated_errors: list[str],
    ) -> None:
        """Process new errors detected since last poll."""
        latest_cumulative_errors_set = set(latest_errors)
        if new_errors_detected := [e for e in polled_errors if e not in latest_cumulative_errors_set]:
            accumulated_errors.extend(new_errors_detected)

    def _validate_active_job(self) -> tuple[int, bool]:
        """Validate that there's an active job and return job_id and success status."""
        return (self.active_job.Id, True) if self.active_job else (0, False)

    def _monitor_job_execution(
        self,
        job_id: int,
        start_time: float,
        timeout_seconds: int,
        accumulated_new_output_builder: list,
        accumulated_new_errors: list,
    ) -> tuple[int, int, str, str, list]:
        """Monitor job execution until completion or timeout."""
        latest_cumulative_output = ""
        latest_cumulative_errors = []
        exit_code = 0
        final_state = JobState.Running
        monitoring_loop_finished = False

        while not monitoring_loop_finished:
            if self._check_shutdown_signal():
                monitoring_loop_finished = True
                continue

            if self._check_timeout(start_time, timeout_seconds):
                monitoring_loop_finished = True
                continue

            current_job_obj = self._get_job_object(job_id)
            if not current_job_obj:
                monitoring_loop_finished, exit_code, final_state = self._handle_job_object_lost(job_id)
                accumulated_new_errors.append("[Job object lost during check]")
                continue

            polled_cumulative_output, polled_cumulative_errors = self._receive_job_output(current_job_obj, keep=True)
            self._process_new_output(
                job_id,
                polled_cumulative_output,
                latest_cumulative_output,
                accumulated_new_output_builder,
            )
            self._process_new_errors(polled_cumulative_errors, latest_cumulative_errors, accumulated_new_errors)

            latest_cumulative_output = polled_cumulative_output
            latest_cumulative_errors = polled_cumulative_errors

            current_state = current_job_obj.JobStateInfo.State
            if current_state not in [JobState.Running, JobState.NotStarted]:
                logger.info("Job %s finished check loop with state: %s", job_id, current_state)
                monitoring_loop_finished = True
                final_state = current_state
                continue

            time.sleep(0.1)

        return exit_code, final_state, latest_cumulative_output, latest_cumulative_errors

    def _collect_final_output(
        self,
        job_id: int,
        latest_cumulative_output: str,
        latest_cumulative_errors: list,
        final_content: str,
        final_errors: list,
        final_state,
    ) -> tuple[str, list, int]:
        """Collect final output from completed job."""
        logger.info("Job %s has finished. Collecting final output.", job_id)

        if final_job_obj := self._get_job_object(job_id):
            final_cumulative_output, final_cumulative_errors = self._receive_job_output(final_job_obj, keep=False)
            final_new_output_chunk = ""

            if final_cumulative_output.startswith(latest_cumulative_output):
                final_new_output_chunk = final_cumulative_output[len(latest_cumulative_output):]
            elif final_cumulative_output:
                final_new_output_chunk = final_cumulative_output.removeprefix(self._last_job_output)

            if final_new_output_chunk.strip():
                final_content = "\n".join(filter(None, [final_content, final_new_output_chunk.strip()]))

            latest_cumulative_errors_set = set(latest_cumulative_errors)
            if new_final_errors := [e for e in final_cumulative_errors if e not in latest_cumulative_errors_set]:
                final_errors.extend(new_final_errors)

            exit_code = 0 if final_state == JobState.Completed else 1
            remove_script = f"Remove-Job -Job (Get-Job -Id {job_id})"
            self._run_ps_command(remove_script)
        else:
            logger.warning("Could not get final job object %s", job_id)
            exit_code = 1

        return final_content, final_errors, exit_code

    def _cleanup_job_state(
        self,
        job_id: int,
        is_finished: bool,
        latest_cumulative_output: str,
        latest_cumulative_errors: list,
    ) -> None:
        """Clean up job state after monitoring."""
        if is_finished:
            if self.active_job and self.active_job.Id == job_id:
                self.active_job = None
            self._last_job_error = []
            self._last_job_output = ""
        else:
            self._last_job_output = latest_cumulative_output
            self._last_job_error = list(set(latest_cumulative_errors))

    def _process_final_errors(
        self,
        final_content: str,
        final_errors: list,
        exit_code: int,
        final_state: int,
    ) -> tuple[str, int]:
        """Process final errors and update content and exit code."""
        if final_errors:
            error_stream_text = "\n".join(final_errors)
            if final_content:
                final_content += f"\n[ERROR STREAM]\n{error_stream_text}"
            else:
                final_content = f"[ERROR STREAM]\n{error_stream_text}"
            if exit_code == 0 and final_state != JobState.Completed:
                exit_code = 1
        return final_content, exit_code

    def _create_output_observation(
        self,
        final_content: str,
        exit_code: int,
        is_finished: bool,
        timeout_seconds: int,
    ) -> CmdOutputObservation:
        """Create the final output observation."""
        current_cwd = self._cwd
        python_safe_cwd = current_cwd.replace("\\\\", "\\\\\\\\")
        metadata = CmdOutputMetadata(exit_code=exit_code, working_dir=python_safe_cwd)
        metadata.prefix = "[Below is the output of the previous command.]\n"

        if is_finished:
            metadata.suffix = f"\n[The command completed with exit code {exit_code}.]"
        else:
            metadata.suffix = f"\n[The command timed out after {timeout_seconds} seconds. {TIMEOUT_MESSAGE_TEMPLATE}]"

        return CmdOutputObservation(content=final_content, command="", metadata=metadata)

    def _check_active_job(self, timeout_seconds: int) -> CmdOutputObservation | ErrorObservation:
        """Checks the active job for new output and status, waiting up to timeout_seconds."""
        with self._job_lock:
            # Validate active job
            job_id, has_active_job = self._validate_active_job()
            if not has_active_job:
                return ErrorObservation(content="ERROR: No previous running command to retrieve logs from.")

            # Initialize job check
            (
                start_time,
                accumulated_new_output_builder,
                accumulated_new_errors,
                exit_code,
                final_state,
                latest_cumulative_output,
                latest_cumulative_errors,
            ) = self._initialize_job_check(job_id, timeout_seconds)

            # Monitor job execution
            exit_code, final_state, latest_cumulative_output, latest_cumulative_errors = self._monitor_job_execution(
                job_id,
                start_time,
                timeout_seconds,
                accumulated_new_output_builder,
                accumulated_new_errors,
            )

            # Determine if job finished
            is_finished = final_state not in [JobState.Running, JobState.NotStarted]
            final_content = "\n".join(accumulated_new_output_builder).strip()
            final_errors = list(accumulated_new_errors)

            # Collect final output if job finished
            if is_finished:
                final_content, final_errors, exit_code = self._collect_final_output(
                    job_id,
                    latest_cumulative_output,
                    latest_cumulative_errors,
                    final_content,
                    final_errors,
                    final_state,
                )

            # Clean up job state
            self._cleanup_job_state(job_id, is_finished, latest_cumulative_output, latest_cumulative_errors)

            # Process final errors
            final_content, exit_code = self._process_final_errors(final_content, final_errors, exit_code, final_state)

            # Create and return observation
            return self._create_output_observation(final_content, exit_code, is_finished, timeout_seconds)

    def _get_current_cwd(self) -> str:
        """Gets the current working directory from the runspace.

        Returns:
            Current working directory path
        """
        results = self._run_ps_command("Get-Location")

        if not results or results.Count == 0:
            logger.error(
                "_get_current_cwd: No valid results received from Get-Location call. Returning cached CWD: %s",
                self._cwd,
            )
            return self._cwd

        first_result = results[0]

        if hasattr(first_result, "Path"):
            return self._process_path_attribute(first_result.Path)
        return self._process_base_object(first_result)

    def _process_path_attribute(self, path) -> str:
        """Process Path attribute from result.

        Args:
            path: Path object from result

        Returns:
            Current working directory
        """
        fetched_cwd = str(path)

        if os.path.isdir(fetched_cwd):
            if fetched_cwd != self._cwd:
                logger.info(
                    "_get_current_cwd: Fetched CWD '%s' differs from cached '%s'. Updating cache.",
                    fetched_cwd,
                    self._cwd,
                )
                self._cwd = fetched_cwd
        else:
            logger.warning(
                "_get_current_cwd: Path '%s' is not a valid directory. Returning cached CWD: %s",
                fetched_cwd,
                self._cwd,
            )

        return self._cwd

    def _process_base_object(self, first_result) -> str:
        """Process BaseObject when Path attribute missing.

        Args:
            first_result: First result from Get-Location

        Returns:
            Current working directory
        """
        try:
            base_object = first_result.BaseObject

            if not hasattr(base_object, "Path"):
                logger.error(
                    "_get_current_cwd: BaseObject also lacks Path attribute. Cannot determine CWD from result: %s",
                    first_result,
                )
                return self._cwd

            fetched_cwd = str(base_object.Path)

            if os.path.isdir(fetched_cwd):
                if fetched_cwd != self._cwd:
                    logger.info(
                        "_get_current_cwd: Fetched CWD '%s' (from BaseObject) differs from cached '%s'. Updating cache.",
                        fetched_cwd,
                        self._cwd,
                    )
                    self._cwd = fetched_cwd
            else:
                logger.warning(
                    "_get_current_cwd: Path '%s' (from BaseObject) is not a valid directory. Returning cached CWD: %s",
                    fetched_cwd,
                    self._cwd,
                )

            return self._cwd

        except AttributeError as ae:
            logger.error("_get_current_cwd: Error accessing BaseObject or its Path: %s. Result: %s", ae, first_result)
            return self._cwd
        except Exception as ex:
            logger.error("_get_current_cwd: Unexpected error checking BaseObject: %s. Result: %s", ex, first_result)
            return self._cwd

    def _handle_active_job(self, command: str, timeout_seconds: int) -> tuple[str, list[str], bool]:
        """Handle active job checking and cleanup if needed."""
        with self._job_lock:
            if not self.active_job:
                return ("", [], False)
            active_job_obj = self._get_job_object(self.active_job.Id)
            job_is_finished = False
            final_output = ""
            final_errors = []
            current_job_state = None
            finished_job_id = self.active_job.Id
            if active_job_obj:
                current_job_state = active_job_obj.JobStateInfo.State
                if current_job_state not in [JobState.Running, JobState.NotStarted]:
                    job_is_finished = True
                    logger.info(
                        "Active job %s was finished (%s) before receiving new command. Cleaning up.",
                        finished_job_id,
                        current_job_state,
                    )
                    final_output, final_errors = self._receive_job_output(active_job_obj, keep=False)
                    remove_script = f"Remove-Job -Job (Get-Job -Id {finished_job_id})"
                    self._run_ps_command(remove_script)
                    self._last_job_output = ""
                    self._last_job_error = []
                    self.active_job = None
            else:
                logger.warning("Active job %s object not found. Assuming finished and cleaning up.", finished_job_id)
                job_is_finished = True
                self._last_job_output = ""
                self._last_job_error = []
                self.active_job = None
            return (final_output, final_errors, True) if job_is_finished else ("", [], False)

    def _execute_ps_command(self, command: str, timeout_seconds: int = 60) -> tuple[str, list[str]]:
        """Execute PowerShell command with timeout handling."""
        ps_command = self._build_ps_command(command)
        result = self._run_ps_command_with_timeout(ps_command, timeout_seconds)
        stdout, stderr = self._parse_ps_result(result)
        return (stdout, stderr)

    def execute(self, action: CmdRunAction) -> CmdOutputObservation | ErrorObservation:
        """Executes a command, potentially as a PowerShell background job for long-running tasks.

        Aligned with bash.py behavior regarding command execution and messages.

        Args:
            action: The command execution action.

        Returns:
            CmdOutputObservation or ErrorObservation.
        """
        if not self._initialized or self._closed:
            return ErrorObservation(content="PowerShell session is not initialized or has been closed.")
        command = action.command.strip()
        timeout_seconds = action.timeout or 60
        is_input = action.is_input
        run_in_background = False
        if command.endswith("&"):
            run_in_background = True
            command = command[:-1].strip()
            logger.info("Detected background command: '%s'", command)
        logger.info(
            "Received command: '%s', Timeout: %ss, is_input: %s, background: %s",
            command,
            timeout_seconds,
            is_input,
            run_in_background,
        )
        stdin_input, job_errors, _job_finished = self._handle_active_job(command, timeout_seconds)
        stdout, stderr = self._execute_ps_command(command, timeout_seconds)
        if run_in_background:
            job_id = self._create_background_job(command)
            return CmdOutputObservation(
                command=command,
                stdout=f"Background job started with ID: {job_id}",
                stderr="".join(job_errors) if job_errors else "",
                exit_code=0,
                timed_out=False,
            )
        exit_code = 1 if stderr else 0
        return CmdOutputObservation(
            command=command,
            stdout=stdout + (stdin_input if is_input else ""),
            stderr=stderr + "".join(job_errors) if job_errors else stderr,
            exit_code=exit_code,
            timed_out=False,
        )

    def close(self) -> None:
        """Closes the PowerShell runspace and releases resources, stopping any active job."""
        if self._closed:
            return
        logger.info("Closing PowerShell session runspace.")
        with self._job_lock:
            if self.active_job:
                logger.warning("Session closing with active job %s. Attempting to stop and remove.", self.active_job.Id)
                job_id = self.active_job.Id
                try:
                    if self._get_job_object(job_id):
                        stop_script = f"Stop-Job -Job (Get-Job -Id {job_id})"
                        self._run_ps_command(stop_script)
                        time.sleep(0.1)
                        remove_script = f"Remove-Job -Job (Get-Job -Id {job_id})"
                        self._run_ps_command(remove_script)
                        logger.info("Stopped and removed active job %s during close.", job_id)
                    else:
                        logger.warning("Could not find job object %s to stop/remove during close.", job_id)
                except Exception as e:
                    logger.error("Error stopping/removing job %s during close: %s", job_id, e)
                self._last_job_output = ""
                self._last_job_error = []
                self.active_job = None
        if hasattr(self, "runspace") and self.runspace:
            try:
                runspace_state_info = self.runspace.RunspaceStateInfo
                if runspace_state_info.State == RunspaceState.Opened:
                    self.runspace.Close()
                self.runspace.Dispose()
                logger.info("PowerShell runspace closed and disposed.")
            except Exception as e:
                logger.error("Error closing/disposing PowerShell runspace: %s", e)
                logger.error(traceback.format_exc())
        self.runspace = None
        self._initialized = False
        self._closed = True

    def __del__(self) -> None:
        """Destructor ensures the runspace is closed."""
        self.close()
