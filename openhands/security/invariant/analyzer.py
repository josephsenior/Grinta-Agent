from __future__ import annotations

import re
import uuid
from typing import Any

import docker

from openhands.core.logger import openhands_logger as logger
from openhands.core.pydantic_compat import model_dump_with_options
from openhands.events.action.action import Action, ActionSecurityRisk
from openhands.security.analyzer import SecurityAnalyzer
from openhands.security.invariant.client import InvariantClient
from openhands.security.invariant.parser import TraceElement, parse_element


class InvariantAnalyzer(SecurityAnalyzer):
    """Security analyzer based on Invariant - purely analytical."""

    trace: list[TraceElement]
    input: list[dict[str, Any]]
    container_name: str = "openhands-invariant-server"
    image_name: str = "ghcr.io/invariantlabs-ai/server:openhands"
    api_host: str = "http://localhost"
    timeout: int = 180

    def __init__(
        self,
        policy: str | None = None,
        sid: str | None = None,
        client: InvariantClient | None = None,
    ) -> None:
        """Initializes a new instance of the InvariantAnalyzer class."""
        super().__init__()
        self._initialize_basic_attributes(sid)
        self._setup_client_and_server(client)
        self._initialize_monitor(policy)

    def _initialize_basic_attributes(self, sid: str | None) -> None:
        """Initialize basic attributes."""
        self.trace = []
        self.input = []
        self.sid = sid if sid is not None else str(uuid.uuid4())
        self.docker_client = None
        self.container = None

    def _setup_client_and_server(self, client: InvariantClient | None) -> None:
        """Set up the invariant client and API server."""
        if client is not None:
            self._use_existing_client(client)
        else:
            self._create_new_client()

    def _use_existing_client(self, client: InvariantClient) -> None:
        """Use an existing client instance."""
        self.client = client
        try:
            self.api_server = getattr(client, "server", None)
        except Exception:
            self.api_server = None

    def _create_new_client(self) -> None:
        """Create a new client with Docker container."""
        self._setup_docker_client()
        if self.docker_client is not None:
            self._setup_container()
            self._get_api_port()
        else:
            self._set_fallback_port()
        self.api_server = f"{self.api_host}:{self.api_port}"
        self.client = InvariantClient(self.api_server, self.sid)

    def _setup_docker_client(self) -> None:
        """Set up Docker client."""
        try:
            self.docker_client = docker.from_env()
        except Exception:
            logger.exception(
                "Error creating Invariant Security Analyzer container. Please check that Docker is running or disable the Security Analyzer in settings.",
                exc_info=False,
            )

    def _setup_container(self) -> None:
        """Set up or create Docker container."""
        if running_containers := self.docker_client.containers.list(filters={"name": self.container_name}):
            self.container = running_containers[0]
        elif all_containers := self.docker_client.containers.list(all=True, filters={"name": self.container_name}):
            self.container = all_containers[0]
            all_containers[0].start()
        else:
            self._create_new_container()
        self._wait_for_container_ready()

    def _create_new_container(self) -> None:
        """Create a new Docker container."""
        from openhands.runtime.utils import find_available_tcp_port

        self.api_port = find_available_tcp_port()
        self.container = self.docker_client.containers.run(
            self.image_name,
            name=self.container_name,
            platform="linux/amd64",
            ports={"8000/tcp": self.api_port},
            detach=True,
        )

    def _wait_for_container_ready(self) -> None:
        """Wait for container to be ready."""
        elapsed = 0
        while self.container is not None and getattr(self.container, "status", None) != "running":
            try:
                self.container = self.docker_client.containers.get(self.container_name)
            except Exception:
                logger.debug("Failed to get invariant container status; falling back to ephemeral port")
                self.container = None
                break
            elapsed += 1
            logger.debug(
                "waiting for container to start: %s, container status: %s",
                elapsed,
                getattr(self.container, "status", None),
            )
            if elapsed > self.timeout:
                break

    def _get_api_port(self) -> None:
        """Get API port from container or fallback."""
        if self.container is not None:
            try:
                self.api_port = int(self.container.attrs["NetworkSettings"]["Ports"]["8000/tcp"][0]["HostPort"])
            except Exception:
                from openhands.runtime.utils import find_available_tcp_port

                self.api_port = find_available_tcp_port()
        else:
            self._set_fallback_port()

    def _set_fallback_port(self) -> None:
        """Set fallback API port."""
        from openhands.runtime.utils import find_available_tcp_port

        self.api_port = find_available_tcp_port()

    def _initialize_monitor(self, policy: str | None) -> None:
        """Initialize the monitor with policy."""
        if policy is None:
            policy, _ = self.client.Policy.get_template()
        if policy is None:
            policy = ""
        self.monitor = self.client.Monitor.from_string(policy)

    async def close(self) -> None:
        if getattr(self, "container", None) is not None:
            try:
                self.container.stop()
            except Exception:
                logger.debug("Failed to stop invariant container during close", exc_info=False)

    def get_risk(self, results: list[str]) -> ActionSecurityRisk:
        mapping = {"high": ActionSecurityRisk.HIGH, "medium": ActionSecurityRisk.MEDIUM, "low": ActionSecurityRisk.LOW}
        regex = "(?<=risk=)\\w+"
        risks: list[ActionSecurityRisk] = []
        for result in results:
            m = re.search(regex, result)
            if m and m.group() in mapping:
                risks.append(mapping[m.group()])
        return max(risks, default=ActionSecurityRisk.LOW)

    async def security_risk(self, action: Action) -> ActionSecurityRisk:
        logger.debug("Calling security_risk on InvariantAnalyzer")
        new_elements = parse_element(self.trace, action)
        input_data = [model_dump_with_options(e, exclude_none=True) for e in new_elements]
        self.trace.extend(new_elements)
        check_result = self.monitor.check(self.input, input_data)
        try:
            if isinstance(check_result, tuple) and len(check_result) == 2:
                result, err = check_result
            else:
                logger.debug("Unexpected monitor.check return type; normalizing", exc_info=False)
                result, err = ([], None)
        except Exception:
            logger.debug("Exception while processing monitor.check result", exc_info=False)
            return ActionSecurityRisk.UNKNOWN
        self.input.extend(input_data)
        if err:
            logger.warning("Error checking policy: %s", err)
            return ActionSecurityRisk.UNKNOWN
        return self.get_risk(result)
