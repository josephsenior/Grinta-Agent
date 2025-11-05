from __future__ import annotations

import base64
import io
import tarfile
import time

import httpx

from openhands.core.exceptions import AgentRuntimeBuildError
from openhands.core.logger import openhands_logger as logger
from openhands.runtime.builder import RuntimeBuilder
from openhands.runtime.utils.request import send_request
from openhands.utils.http_session import HttpSession
from openhands.utils.shutdown_listener import should_continue, sleep_if_should_continue


class RemoteRuntimeBuilder(RuntimeBuilder):
    """This class interacts with the remote Runtime API for building and managing container images."""

    def __init__(self, api_url: str, api_key: str, session: HttpSession | None = None) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.session = session or HttpSession()
        self.session.headers.update({"X-API-Key": self.api_key})

    def build(
        self,
        path: str,
        tags: list[str],
        platform: str | None = None,
        extra_build_args: list[str] | None = None,
    ) -> str:
        """Builds a Docker image using the Runtime API's /build endpoint."""
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
            tar.add(path, arcname=".")
        tar_buffer.seek(0)
        base64_encoded_tar = base64.b64encode(tar_buffer.getvalue()).decode("utf-8")
        files = [("context", ("context.tar.gz", base64_encoded_tar)), ("target_image", (None, tags[0]))]
        files.extend(("tags", (None, tag)) for tag in tags[1:])
        try:
            response = send_request(self.session, "POST", f"{self.api_url}/build", files=files, timeout=30)
        except httpx.HTTPError as e:
            if e.response.status_code != 429:
                raise
            logger.warning("Build was rate limited. Retrying in 30 seconds.")
            time.sleep(30)
            return self.build(path, tags, platform)
        build_data = response.json()
        build_id = build_data["build_id"]
        logger.info("Build initiated with ID: %s", build_id)
        start_time = time.time()
        timeout = 30 * 60
        while should_continue():
            if time.time() - start_time > timeout:
                logger.error("Build timed out after 30 minutes")
                msg = "Build timed out after 30 minutes"
                raise AgentRuntimeBuildError(msg)
            status_response = send_request(
                self.session,
                "GET",
                f"{self.api_url}/build_status",
                params={"build_id": build_id},
            )
            if status_response.status_code != 200:
                logger.error("Failed to get build status: %s", status_response.text)
                msg = f"Failed to get build status: {status_response.text}"
                raise AgentRuntimeBuildError(msg)
            status_data = status_response.json()
            status = status_data["status"]
            logger.info("Build status: %s", status)
            if status == "SUCCESS":
                logger.debug("Successfully built %s", status_data["image"])
                return str(status_data["image"])
            if status in ["FAILURE", "INTERNAL_ERROR", "TIMEOUT", "CANCELLED", "EXPIRED"]:
                error_message = status_data.get("error", f"Build failed with status: {status}. Build ID: {build_id}")
                logger.error(error_message)
                raise AgentRuntimeBuildError(error_message)
            sleep_if_should_continue(30)
        msg = "Build interrupted"
        raise AgentRuntimeBuildError(msg)

    def image_exists(self, image_name: str, pull_from_repo: bool = True) -> bool:
        """Checks if an image exists in the remote registry using the /image_exists endpoint."""
        params = {"image": image_name}
        response = send_request(self.session, "GET", f"{self.api_url}/image_exists", params=params)
        if response.status_code != 200:
            logger.error("Failed to check image existence: %s", response.text)
            msg = f"Failed to check image existence: {response.text}"
            raise AgentRuntimeBuildError(msg)
        result = response.json()
        if result["exists"]:
            logger.debug(
                "Image %s exists. Uploaded at: %s, Size: %s MB",
                image_name,
                result["image"]["upload_time"],
                result["image"]["image_size_bytes"] / 1024 / 1024,
            )
        else:
            logger.debug("Image %s does not exist.", image_name)
        return bool(result["exists"])
