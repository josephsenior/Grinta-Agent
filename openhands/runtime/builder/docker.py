from __future__ import annotations

import datetime
import os
import subprocess
import time

import docker

from openhands import __version__ as oh_version
from openhands.core.exceptions import AgentRuntimeBuildError
from openhands.core.logger import RollingLogger
from openhands.core.logger import openhands_logger as logger
from openhands.runtime.builder.base import RuntimeBuilder
from openhands.utils.term_color import TermColor, colorize


def _docker_validate_server_version(version_info):
    server_version = version_info.get("Version", "").split("+")[0].replace("-", ".")
    is_podman = version_info.get("Components")[0].get("Name").startswith("Podman")
    if tuple(map(int, (server_version or "").split(".")[:2])) < (18, 9) and (not is_podman):
        msg = "Docker server version must be >= 18.09 to use BuildKit"
        raise AgentRuntimeBuildError(msg)
    if is_podman and tuple(map(int, (server_version or "").split(".")[:2])) < (4, 9):
        msg = "Podman server version must be >= 4.9.0"
        raise AgentRuntimeBuildError(msg)
    return is_podman, server_version


def _docker_run_install_commands(commands) -> None:
    for cmd in commands:
        try:
            cmd_args = cmd.split() if isinstance(cmd, str) else cmd
            subprocess.run(cmd_args, shell=False, check=True, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            logger.error("Image build failed: %s", e)
            logger.error("Command output: %s", getattr(e, "output", None))
            raise


class DockerRuntimeBuilder(RuntimeBuilder):

    def __init__(self, docker_client: docker.DockerClient) -> None:
        self.docker_client = docker_client
        version_info = self.docker_client.version()
        server_version = version_info.get("Version", "").replace("-", ".")
        self.is_podman = version_info.get("Components")[0].get("Name").startswith("Podman")
        if tuple(map(int, server_version.split(".")[:2])) < (18, 9) and (not self.is_podman):
            msg = "Docker server version must be >= 18.09 to use BuildKit"
            raise AgentRuntimeBuildError(msg)
        if self.is_podman and tuple(map(int, server_version.split(".")[:2])) < (4, 9):
            msg = "Podman server version must be >= 4.9.0"
            raise AgentRuntimeBuildError(msg)
        self.rolling_logger = RollingLogger(max_lines=10)

    @staticmethod
    def check_buildx(is_podman: bool = False) -> bool:
        """Check if Docker Buildx is available."""
        try:
            result = subprocess.run(
                ["podman" if is_podman else "docker", "buildx", "version"],
                check=False,
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _initialize_docker_client(self) -> None:
        """Initialize Docker client and check version compatibility."""
        self.docker_client = docker.from_env()
        version_info = self.docker_client.version()
        server_version = version_info.get("Version", "").split("+")[0].replace("-", ".")
        self.is_podman = version_info.get("Components")[0].get("Name").startswith("Podman")

        if tuple(map(int, server_version.split("."))) < (18, 9) and (not self.is_podman):
            msg = "Docker server version must be >= 18.09 to use BuildKit"
            raise AgentRuntimeBuildError(msg)
        if self.is_podman and tuple(map(int, server_version.split("."))) < (4, 9):
            msg = "Podman server version must be >= 4.9.0"
            raise AgentRuntimeBuildError(msg)

    def _install_docker_if_needed(self) -> None:
        """Install Docker if buildx is not available."""
        if not DockerRuntimeBuilder.check_buildx(self.is_podman):
            logger.info("No docker binary available inside openhands-app container, trying to download online...")
            commands = [
                "apt-get update",
                "apt-get install -y ca-certificates curl gnupg",
                "install -m 0755 -d /etc/apt/keyrings",
                "curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc",
                "chmod a+r /etc/apt/keyrings/docker.asc",
                'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null',
                "apt-get update",
                "apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin",
            ]
            _docker_run_install_commands(commands)
            logger.info("Downloaded and installed docker binary")

    def _parse_image_tags(self, tags: list[str]) -> tuple[str, str, str | None]:
        """Parse image tags and return hash name, repo, source tag, and optional tag."""
        target_image_hash_name = tags[0]
        target_image_repo, target_image_source_tag = target_image_hash_name.split(":")
        target_image_tag = tags[1].split(":")[1] if len(tags) > 1 else None
        return target_image_hash_name, target_image_repo, target_image_source_tag, target_image_tag

    def _build_docker_command(
        self,
        target_image_hash_name: str,
        platform: str | None,
        use_local_cache: bool,
        extra_build_args: list[str] | None,
        path: str,
    ) -> list[str]:
        """Build the Docker buildx command."""
        buildx_cmd = [
            "podman" if self.is_podman else "docker",
            "buildx",
            "build",
            "--progress=plain",
            f"--build-arg=OPENHANDS_RUNTIME_VERSION={oh_version}",
            f"--build-arg=OPENHANDS_RUNTIME_BUILD_TIME={datetime.datetime.now().isoformat()}",
            f"--tag={target_image_hash_name}",
            "--load",
        ]

        if platform:
            buildx_cmd.append(f"--platform={platform}")

        cache_dir = "/tmp/.buildx-cache"  # nosec B108 - Safe: Docker build cache directory
        if use_local_cache and self._is_cache_usable(cache_dir):
            buildx_cmd.extend(
                [f"--cache-from=type=local,src={cache_dir}", f"--cache-to=type=local,dest={cache_dir},mode=max"],
            )

        if extra_build_args:
            buildx_cmd.extend(extra_build_args)

        buildx_cmd.append(path)
        return buildx_cmd

    def _set_default_builder(self) -> None:
        """Set the default Docker buildx builder."""
        builder_cmd = ["docker", "buildx", "use", "default"]
        subprocess.Popen(builder_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

    def _process_build_output(self, process: subprocess.Popen[str]) -> list[str]:
        """Process the build command output and collect log lines.

        Args:
            process: The subprocess running the build command.

        Returns:
            list[str]: List of output lines from the build process.
        """
        output_lines = []

        if process.stdout:
            for line in iter(process.stdout.readline, ""):
                if line := line.strip():
                    output_lines.append(line)
                    self._output_logs(line)

        return output_lines

    def _handle_build_exceptions(self, e: Exception) -> None:
        """Handle various exceptions that can occur during the build process.

        Args:
            e: The exception that occurred.
        """
        if isinstance(e, subprocess.CalledProcessError):
            logger.error("Image build failed with exit code %s", e.returncode)
            if e.output:
                logger.error("Command output:\n%s", e.output)
            elif self.rolling_logger.is_enabled() and self.rolling_logger.all_lines:
                logger.error("Docker build output:\n%s", self.rolling_logger.all_lines)
        elif isinstance(e, subprocess.TimeoutExpired):
            logger.error("Image build timed out")
        elif isinstance(e, FileNotFoundError):
            logger.error("Python executable not found: %s", e)
        elif isinstance(e, PermissionError):
            logger.error("Permission denied when trying to execute the build command:\n%s", e)
        else:
            logger.error("An unexpected error occurred during the build process: %s", e)

    def _execute_build_command(self, buildx_cmd: list[str]) -> None:
        """Execute the Docker build command and handle output.

        Args:
            buildx_cmd: The Docker build command to execute.

        Raises:
            subprocess.CalledProcessError: If the build command fails.
            subprocess.TimeoutExpired: If the build times out.
            FileNotFoundError: If required executables are not found.
            PermissionError: If there are permission issues.
            Exception: For any other unexpected errors.
        """
        self.rolling_logger.start(f"================ {buildx_cmd[0].upper()} BUILD STARTED ================")

        # Set default builder
        self._set_default_builder()

        try:
            process = subprocess.Popen(
                buildx_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )

            # Process output and collect lines
            output_lines = self._process_build_output(process)

            # Check return code
            return_code = process.wait()
            if return_code != 0:
                output_str = "\n".join(output_lines)
                raise subprocess.CalledProcessError(return_code, process.args, output=output_str, stderr=None)

        except Exception as e:
            self._handle_build_exceptions(e)
            raise

    def _tag_and_validate_image(
        self,
        target_image_hash_name: str,
        target_image_repo: str,
        target_image_source_tag: str,
        target_image_tag: str | None,
    ) -> str:
        """Tag the image and validate it was built successfully."""
        logger.info("Image [%s] build finished.", target_image_hash_name)

        if target_image_tag:
            image = self.docker_client.images.get(target_image_hash_name)
            image.tag(target_image_repo, target_image_tag)
            logger.info("Re-tagged image [%s] with more generic tag [%s]", target_image_hash_name, target_image_tag)

        image = self.docker_client.images.get(target_image_hash_name)
        if image is None:
            msg = f"Build failed: Image {target_image_hash_name} not found"
            raise AgentRuntimeBuildError(msg)

        tags_str = f"{target_image_source_tag}, {target_image_tag}" if target_image_tag else target_image_source_tag
        logger.info("Image %s with tags [%s] built successfully", target_image_repo, tags_str)

        return target_image_hash_name

    def build(
        self,
        path: str,
        tags: list[str],
        platform: str | None = None,
        extra_build_args: list[str] | None = None,
        use_local_cache: bool = False,
    ) -> str:
        """Builds a Docker image using BuildKit and handles the build logs appropriately.

        Args:
            path (str): The path to the Docker build context.
            tags (list[str]): A list of image tags to apply to the built image.
            platform (str, optional): The target platform for the build. Defaults to None.
            use_local_cache (bool, optional): Whether to use and update the local build cache. Defaults to True.
            extra_build_args (list[str], optional): Additional arguments to pass to the Docker build command. Defaults to None.

        Returns:
            str: The name of the built Docker image.

        Raises:
            AgentRuntimeBuildError: If the Docker server version is incompatible or if the build process fails.

        Note:
            This method uses Docker BuildKit for improved build performance and caching capabilities.
            If `use_local_cache` is True, it will attempt to use and update the build cache in a local directory.
            The `extra_build_args` parameter allows for passing additional Docker build arguments as needed.
        """
        # Initialize Docker client and check version
        self._initialize_docker_client()

        # Install Docker if needed
        self._install_docker_if_needed()

        # Parse image tags
        target_image_hash_name, target_image_repo, target_image_source_tag, target_image_tag = self._parse_image_tags(
            tags,
        )

        # Build Docker command
        buildx_cmd = self._build_docker_command(
            target_image_hash_name,
            platform,
            use_local_cache,
            extra_build_args,
            path,
        )

        # Execute build command
        self._execute_build_command(buildx_cmd)

        # Tag and validate image
        return self._tag_and_validate_image(
            target_image_hash_name,
            target_image_repo,
            target_image_source_tag,
            target_image_tag,
        )

    def image_exists(self, image_name: str, pull_from_repo: bool = True) -> bool:
        """Check if the image exists in the registry (try to pull it first) or in the local store.

        Args:
            image_name (str): The Docker image to check (<image repo>:<image tag>)
            pull_from_repo (bool): Whether to pull from the remote repo if the image not present locally
        Returns:
            bool: Whether the Docker image exists in the registry or in the local store
        """
        if not image_name:
            logger.error("Invalid image name: `%s`", image_name)
            return False
        try:
            logger.debug("Checking, if image exists locally:\n%s", image_name)
            self.docker_client.images.get(image_name)
            logger.debug("Image found locally.")
            return True
        except docker.errors.ImageNotFound:
            if not pull_from_repo:
                logger.debug("Image %s %s locally", image_name, colorize("not found", TermColor.WARNING))
                return False
            try:
                logger.debug("Image not found locally. Trying to pull it, please wait...")
                layers: dict[str, dict[str, str]] = {}
                previous_layer_count = 0
                if ":" in image_name:
                    image_repo, image_tag = image_name.split(":", 1)
                else:
                    image_repo = image_name
                    image_tag = None
                for line in self.docker_client.api.pull(image_repo, tag=image_tag, stream=True, decode=True):
                    self._output_build_progress(line, layers, previous_layer_count)
                    previous_layer_count = len(layers)
                logger.debug("Image pulled")
                return True
            except docker.errors.ImageNotFound:
                logger.debug("Could not find image locally or in registry.")
                return False
            except Exception as e:
                msg = f"Image {colorize('could not be pulled', TermColor.ERROR)}: "
                ex_msg = str(e)
                msg += "image not found in registry." if "Not Found" in ex_msg else f"{ex_msg}"
                logger.debug(msg)
                return False

    def _output_logs(self, new_line: str) -> None:
        if not self.rolling_logger.is_enabled():
            logger.debug(new_line)
        else:
            self.rolling_logger.add_line(new_line)

    def _output_build_progress(self, current_line: dict, layers: dict, previous_layer_count: int) -> None:
        """Output build progress for Docker layers."""
        if "id" in current_line and "progressDetail" in current_line:
            self._process_layer_progress(current_line, layers, previous_layer_count)
        elif "status" in current_line:
            logger.debug(current_line["status"])

    def _process_layer_progress(self, current_line: dict, layers: dict, previous_layer_count: int) -> None:
        """Process progress for a specific layer."""
        layer_id = current_line["id"]

        # Initialize layer data if not exists
        if layer_id not in layers:
            layers[layer_id] = {"status": "", "progress": "", "last_logged": 0}

        # Update layer status and progress
        self._update_layer_data(layer_id, current_line, layers)

        # Calculate percentage
        percentage = self._calculate_layer_percentage(current_line, layers[layer_id])

        # Output progress
        self._output_layer_progress(layer_id, layers, previous_layer_count, percentage)

    def _update_layer_data(self, layer_id: str, current_line: dict, layers: dict) -> None:
        """Update layer data with current line information."""
        if "status" in current_line:
            layers[layer_id]["status"] = current_line["status"]
        if "progress" in current_line:
            layers[layer_id]["progress"] = current_line["progress"]

    def _calculate_layer_percentage(self, current_line: dict, layer_data: dict) -> float:
        """Calculate percentage for layer progress."""
        if "progressDetail" in current_line:
            progress_detail = current_line["progressDetail"]
            if "total" not in progress_detail or "current" not in progress_detail:
                return 100 if layer_data["status"] == "Download complete" else 0
            total = progress_detail["total"]
            return min(progress_detail["current"] / total * 100, 100)
        return 0

    def _output_layer_progress(self, layer_id: str, layers: dict, previous_layer_count: int, percentage: float) -> None:
        """Output progress for the layer."""
        if self.rolling_logger.is_enabled():
            self._output_rolling_logger_progress(layers, previous_layer_count)
        else:
            self._output_debug_logger_progress(layer_id, layers, percentage)

        layers[layer_id]["last_logged"] = percentage

    def _output_rolling_logger_progress(self, layers: dict, previous_layer_count: int) -> None:
        """Output progress using rolling logger."""
        self.rolling_logger.move_back(previous_layer_count)

        for lid, layer_data in sorted(layers.items()):
            self.rolling_logger.replace_current_line()
            status = layer_data["status"]
            progress = layer_data["progress"]

            if status == "Download complete":
                self.rolling_logger.write_immediately(f"Layer {lid}: Download complete")
            elif status == "Already exists":
                self.rolling_logger.write_immediately(f"Layer {lid}: Already exists")
            else:
                self.rolling_logger.write_immediately(f"Layer {lid}: {progress} {status}")

    def _output_debug_logger_progress(self, layer_id: str, layers: dict, percentage: float) -> None:
        """Output progress using debug logger."""
        if percentage != 0 and (percentage - layers[layer_id]["last_logged"] >= 10 or percentage == 100):
            logger.debug("Layer %s: %s %s", layer_id, layers[layer_id]["progress"], layers[layer_id]["status"])

    def _prune_old_cache_files(self, cache_dir: str, max_age_days: int = 7) -> None:
        """Prune cache files older than the specified number of days.

        Args:
            cache_dir (str): The path to the cache directory.
            max_age_days (int): The maximum age of cache files in days.
        """
        try:
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60
            for root, _, files in os.walk(cache_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > max_age_seconds:
                            os.remove(file_path)
                            logger.debug("Removed old cache file: %s", file_path)
                    except Exception as e:
                        logger.warning("Error processing cache file %s: %s", file_path, e)
        except Exception as e:
            logger.warning("Error during build cache pruning: %s", e)

    def _is_cache_usable(self, cache_dir: str) -> bool:
        """Check if the cache directory is usable (exists and is writable).

        Args:
            cache_dir (str): The path to the cache directory.

        Returns:
            bool: True if the cache directory is usable, False otherwise.
        """
        if not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir, exist_ok=True)
                logger.debug("Created cache directory: %s", cache_dir)
            except OSError as e:
                logger.debug("Failed to create cache directory %s: %s", cache_dir, e)
                return False
        if not os.access(cache_dir, os.W_OK):
            logger.warning("Cache directory %s is not writable. Caches will not be used for Docker builds.", cache_dir)
            return False
        self._prune_old_cache_files(cache_dir)
        logger.debug("Cache directory %s is usable", cache_dir)
        return True
