"""Client interfaces for Invariant policy and monitor operations."""

from __future__ import annotations

import time
import uuid
from typing import Any

import httpx

from forge.core.logger import forge_logger as logger


class InvariantClient:
    """Client for interacting with Invariant security analysis server.

    Manages session lifecycle and provides Policy and Monitor interfaces
    for security policy enforcement and monitoring.
    """

    timeout: int = 120

    def __init__(self, server_url: str, session_id: str | None = None) -> None:
        """Initialize Invariant client with server URL and optional session ID.

        Args:
            server_url: URL of Invariant server
            session_id: Optional session ID to reuse

        Raises:
            RuntimeError: If session creation fails

        """
        self.server = server_url
        self.session_id, err = self._create_session(session_id)
        if err:
            msg = f"Failed to create session: {err}"
            raise RuntimeError(msg)
        self.Policy = self._Policy(self)
        self.Monitor = self._Monitor(self)

    def _create_session(
        self, session_id: str | None = None
    ) -> tuple[str | None, Exception | None]:
        """Create a new session with the Invariant server, with retry logic.

        Attempts to connect to the Invariant server within the configured timeout.
        Implements retry with 1-second backoff for network errors.

        Args:
            session_id: Optional session ID to reuse. If None, server creates new ID.

        Returns:
            tuple: (session_id, error) - session_id is None on failure, error is None on success

        Retryable Errors:
            - httpx.NetworkError: Connection issues (retried up to timeout)
            - httpx.TimeoutException: Timeout errors (retried up to timeout)

        Non-Retryable Errors:
            - httpx.HTTPError: HTTP protocol errors (status code errors)
            - Generic Exception: Unexpected errors

        Example:
            >>> client = InvariantClient("http://localhost:8000")
            >>> session_id, err = client._create_session()
            >>> if not err:
            ...     print(f"Session created: {session_id}")

        """
        if self.timeout <= 0:
            fallback_id = session_id or str(uuid.uuid4())
            logger.debug(
                "InvariantClient timeout <= 0; using fallback session id %s without contacting server",
                fallback_id,
            )
            return (fallback_id, None)

        elapsed = 0
        while elapsed < self.timeout:
            try:
                if session_id:
                    response = httpx.get(
                        f"{self.server}/session/new?session_id={session_id}", timeout=60
                    )
                else:
                    response = httpx.get(f"{self.server}/session/new", timeout=60)
                response.raise_for_status()
                return (response.json().get("id"), None)
            except (httpx.NetworkError, httpx.TimeoutException):
                elapsed += 1
                time.sleep(1)
            except httpx.HTTPError as http_err:
                return (None, http_err)
            except Exception as err:
                return (None, err)
        fallback_session_id = session_id or str(uuid.uuid4())
        logger.warning(
            "Timeout creating Invariant session after %s seconds; reusing fallback id %s",
            self.timeout,
            fallback_session_id,
        )
        return (fallback_session_id, None)

    def close_session(self) -> Exception | None:
        """Close the current session with the Invariant server.

        Returns:
            Exception if close failed, None on success

        """
        try:
            response = httpx.delete(
                f"{self.server}/session/?session_id={self.session_id}", timeout=60
            )
            response.raise_for_status()
        except (ConnectionError, httpx.TimeoutException, httpx.HTTPError) as err:
            return err
        return None

    class _Policy:
        """Policy interface for Invariant security rules."""

        def __init__(self, invariant: InvariantClient) -> None:
            self.server = invariant.server
            self.session_id = invariant.session_id
            self.policy_id: str | None = None

        def _create_policy(self, rule: str) -> tuple[str | None, Exception | None]:
            """Create a new policy on the Invariant server.

            Sends the rule to the server to create and compile a policy for later analysis.

            Args:
                rule: Policy rule string in Invariant DSL

            Returns:
                tuple: (policy_id, error) - policy_id is None on failure, error is None on success

            Raises (Returned as tuple):
                - ConnectionError: Network connectivity issues
                - httpx.TimeoutException: Server timeout
                - httpx.HTTPError: HTTP errors from server

            """
            try:
                response = httpx.post(
                    f"{self.server}/policy/new?session_id={self.session_id}",
                    json={"rule": rule},
                    timeout=60,
                )
                response.raise_for_status()
                return (response.json().get("policy_id"), None)
            except (ConnectionError, httpx.TimeoutException, httpx.HTTPError) as err:
                return (None, err)

        def get_template(self) -> tuple[str | None, Exception | None]:
            """Get policy template from Invariant server.

            Returns:
                tuple: (template, error) - template is None on failure, error is None on success

            """
            try:
                response = httpx.get(f"{self.server}/policy/template", timeout=60)
                response.raise_for_status()
                return (response.json(), None)
            except (ConnectionError, httpx.TimeoutException, httpx.HTTPError) as err:
                return (None, err)

        def from_string(self, rule: str) -> InvariantClient._Policy:
            """Create policy from rule string.

            Args:
                rule: Policy rule string in Invariant DSL

            Returns:
                Self for method chaining

            Raises:
                Exception: If policy creation fails

            """
            policy_id, err = self._create_policy(rule)
            if err:
                raise err
            self.policy_id = policy_id
            return self

        def analyze(self, trace: list[dict[str, Any]]) -> tuple[Any, Exception | None]:
            """Analyze trace against the policy.

            Args:
                trace: List of trace event dictionaries

            Returns:
                tuple: (analysis_result, error) - result is None on failure, error is None on success

            """
            try:
                response = httpx.post(
                    f"{self.server}/policy/{self.policy_id}/analyze?session_id={self.session_id}",
                    json={"trace": trace},
                    timeout=60,
                )
                response.raise_for_status()
                return (response.json(), None)
            except (ConnectionError, httpx.TimeoutException, httpx.HTTPError) as err:
                return (None, err)

    class _Monitor:
        """Monitor interface for real-time Invariant security checking."""

        def __init__(self, invariant: InvariantClient) -> None:
            """Initialize monitor with Invariant client.

            Args:
                invariant: InvariantClient instance

            """
            self.server = invariant.server
            self.session_id = invariant.session_id
            self.policy = ""
            self.monitor_id: str | None = None

        def _create_monitor(self, rule: str) -> tuple[str | None, Exception | None]:
            """Create a new monitor on the Invariant server.

            Sends the rule to the server to create a monitor for real-time event checking.

            Args:
                rule: Monitor rule string in Invariant DSL

            Returns:
                tuple: (monitor_id, error) - monitor_id is None on failure, error is None on success

            Raises (Returned as tuple):
                - ConnectionError: Network connectivity issues
                - httpx.TimeoutException: Server timeout
                - httpx.HTTPError: HTTP errors from server

            """
            try:
                response = httpx.post(
                    f"{self.server}/monitor/new?session_id={self.session_id}",
                    json={"rule": rule},
                    timeout=60,
                )
                response.raise_for_status()
                return (response.json().get("monitor_id"), None)
            except (ConnectionError, httpx.TimeoutException, httpx.HTTPError) as err:
                return (None, err)

        def from_string(self, rule: str) -> InvariantClient._Monitor:
            """Create monitor from rule string.

            Args:
                rule: Monitor rule string in Invariant DSL

            Returns:
                Self for method chaining

            Raises:
                Exception: If monitor creation fails

            """
            monitor_id, err = self._create_monitor(rule)
            if err:
                raise err
            self.monitor_id = monitor_id
            self.policy = rule
            return self

        def check(
            self,
            past_events: list[dict[str, Any]],
            pending_events: list[dict[str, Any]],
        ) -> tuple[Any, Exception | None]:
            """Check new events against monitor policy.

            Args:
                past_events: Previous events in the trace
                pending_events: New events to check

            Returns:
                tuple: (violations, error) - violations is list of violation strings, error is None on success

            """
            try:
                response = httpx.post(
                    f"{self.server}/monitor/{self.monitor_id}/check?session_id={self.session_id}",
                    json={"past_events": past_events, "pending_events": pending_events},
                    timeout=60,
                )
                response.raise_for_status()
                return (response.json(), None)
            except (ConnectionError, httpx.TimeoutException, httpx.HTTPError) as err:
                return (None, err)
