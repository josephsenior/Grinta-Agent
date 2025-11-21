"""Alert policies and SLO tracking with Prometheus integration."""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from typing import Any
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)

# Global alerting configuration
_alerting_initialized = False
_alert_client: Any | None = None


class AlertPolicy:
    """Alert policy with threshold and action."""

    def __init__(
        self,
        name: str,
        metric: str,
        threshold: float,
        comparison: str = ">",
        duration: float = 60.0,
        enabled: bool = True,
    ) -> None:
        """Initialize alert policy.

        Args:
            name: Alert policy name
            metric: Metric name to monitor
            threshold: Alert threshold
            comparison: Comparison operator ('>', '<', '>=', '<=', '==')
            duration: Duration in seconds before alerting
            enabled: Whether alert is enabled

        """
        self.name = name
        self.metric = metric
        self.threshold = threshold
        self.comparison = comparison
        self.duration = duration
        self.enabled = enabled
        self._violation_start_time: float | None = None
        self._last_alert_time: float | None = None
        self._alert_cooldown = 300.0  # 5 minutes cooldown

    def check(self, value: float) -> bool:
        """Check if metric value violates policy."""
        if not self.enabled:
            return False

        if not self._is_threshold_violated(value):
            self._violation_start_time = None
            return False

        if not self._violation_start_time:
            self._violation_start_time = time.time()
            return False

        if not self._has_duration_passed():
            return False

        if not self._is_cooldown_complete():
            return False

        self._violation_start_time = None
        self._last_alert_time = time.time()
        return True

    def _is_threshold_violated(self, value: float) -> bool:
        comparisons = {
            ">": value > self.threshold,
            "<": value < self.threshold,
            ">=": value >= self.threshold,
            "<=": value <= self.threshold,
            "==": value == self.threshold,
        }
        return comparisons.get(self.comparison, False)

    def _has_duration_passed(self) -> bool:
        assert self._violation_start_time is not None
        return (time.time() - self._violation_start_time) >= self.duration

    def _is_cooldown_complete(self) -> bool:
        if self._last_alert_time is None:
            return True
        return (time.time() - self._last_alert_time) >= self._alert_cooldown

    def reset(self) -> None:
        """Reset alert policy state."""
        self._violation_start_time = None
        self._last_alert_time = None


class SLOTracker:
    """SLO tracker for availability, latency, and error rate."""

    def __init__(
        self,
        availability_target: float = 0.99,
        latency_p95_target_ms: float = 1000.0,
        error_rate_target: float = 0.01,
    ) -> None:
        """Initialize SLO tracker.

        Args:
            availability_target: Availability SLO target (0.0 to 1.0)
            latency_p95_target_ms: P95 latency SLO target in milliseconds
            error_rate_target: Error rate SLO target (0.0 to 1.0)

        """
        self.availability_target = availability_target
        self.latency_p95_target_ms = latency_p95_target_ms
        self.error_rate_target = error_rate_target

        self._request_count = 0
        self._error_count = 0
        self._latency_samples: list[float] = []
        self._window_start_time = time.time()
        self._window_duration = 300.0  # 5 minutes

    def record_request(self, latency_ms: float, is_error: bool = False) -> None:
        """Record request for SLO tracking.

        Args:
            latency_ms: Request latency in milliseconds
            is_error: Whether request resulted in error

        """
        self._request_count += 1
        if is_error:
            self._error_count += 1
        self._latency_samples.append(latency_ms)

        # Reset window if expired
        if time.time() - self._window_start_time >= self._window_duration:
            self._reset_window()

    def get_availability(self) -> float:
        """Get current availability.

        Returns:
            Availability (0.0 to 1.0)

        """
        if self._request_count == 0:
            return 1.0
        return 1.0 - (self._error_count / self._request_count)

    def get_latency_p95(self) -> float:
        """Get P95 latency.

        Returns:
            P95 latency in milliseconds

        """
        if not self._latency_samples:
            return 0.0
        sorted_samples = sorted(self._latency_samples)
        p95_index = int(len(sorted_samples) * 0.95)
        return sorted_samples[p95_index]

    def get_error_rate(self) -> float:
        """Get error rate.

        Returns:
            Error rate (0.0 to 1.0)

        """
        if self._request_count == 0:
            return 0.0
        return self._error_count / self._request_count

    def check_slo_violations(self) -> dict[str, bool | float]:
        """Check SLO violations.

        Returns:
            Dict with SLO violation status

        """
        availability = self.get_availability()
        latency_p95 = self.get_latency_p95()
        error_rate = self.get_error_rate()

        return {
            "availability": availability < self.availability_target,
            "latency": latency_p95 > self.latency_p95_target_ms,
            "error_rate": error_rate > self.error_rate_target,
            "availability_value": availability,
            "latency_p95_value": latency_p95,
            "error_rate_value": error_rate,
        }

    def _reset_window(self) -> None:
        """Reset SLO tracking window."""
        self._request_count = 0
        self._error_count = 0
        self._latency_samples.clear()
        self._window_start_time = time.time()


class AlertClient:
    """Alert client for sending alerts to external services."""

    def __init__(
        self,
        endpoint: str | None = None,
        api_key: str | None = None,
        enabled: bool = False,
    ) -> None:
        """Initialize alert client.

        Args:
            endpoint: Alert endpoint URL
            api_key: API key for alert service
            enabled: Whether alerting is enabled

        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.enabled = enabled
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10.0)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def send_alert(
        self,
        policy_name: str,
        metric: str,
        value: float,
        threshold: float,
        message: str | None = None,
    ) -> bool:
        """Send alert to external service.

        Args:
            policy_name: Alert policy name
            metric: Metric name
            value: Current metric value
            threshold: Alert threshold
            message: Optional alert message

        Returns:
            True if successful, False otherwise

        """
        if not self._can_send_alert():
            return False

        try:
            session = await self._get_session()
            parsed_endpoint = urlparse(self.endpoint)
            headers = self._build_headers(parsed_endpoint)
            payload = self._build_payload(
                parsed_endpoint, policy_name, metric, value, threshold, message
            )
            return await self._execute_alert_request(session, headers, payload, policy_name, metric, value)
        except Exception as e:
            logger.error(f"Error sending alert: {e}", exc_info=True)
            return False

    def _can_send_alert(self) -> bool:
        return bool(self.enabled and self.endpoint)

    def _build_headers(self, parsed_endpoint) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if not self.api_key:
            return headers

        host = parsed_endpoint.netloc.lower()
        if "pagerduty" in host:
            headers["Authorization"] = f"Token token={self.api_key}"
        else:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _build_payload(
        self,
        parsed_endpoint,
        policy_name: str,
        metric: str,
        value: float,
        threshold: float,
        message: str | None,
    ) -> dict[str, Any]:
        host = parsed_endpoint.netloc.lower()
        if "pagerduty" in host:
            return self._pagerduty_payload(policy_name, metric, value, threshold, message)
        if "slack" in host:
            return self._slack_payload(policy_name, metric, value, threshold, message)
        return self._generic_payload(policy_name, metric, value, threshold, message)

    def _pagerduty_payload(
        self, policy_name: str, metric: str, value: float, threshold: float, message: str | None
    ) -> dict[str, Any]:
        summary = message or f"{policy_name}: {metric} = {value} (threshold: {threshold})"
        return {
            "routing_key": self.api_key,
            "event_action": "trigger",
            "payload": {
                "summary": summary,
                "severity": "error",
                "source": "forge",
                "custom_details": {
                    "policy": policy_name,
                    "metric": metric,
                    "value": value,
                    "threshold": threshold,
                },
            },
        }

    def _slack_payload(
        self, policy_name: str, metric: str, value: float, threshold: float, message: str | None
    ) -> dict[str, Any]:
        text = message or f"{metric} = {value} (threshold: {threshold})"
        return {
            "text": f"Alert: {policy_name}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{policy_name}*\n{text}",
                    },
                }
            ],
        }

    def _generic_payload(
        self, policy_name: str, metric: str, value: float, threshold: float, message: str | None
    ) -> dict[str, Any]:
        return {
            "policy": policy_name,
            "metric": metric,
            "value": value,
            "threshold": threshold,
            "message": message,
            "timestamp": time.time(),
        }

    async def _execute_alert_request(
        self,
        session: aiohttp.ClientSession,
        headers: dict[str, str],
        payload: dict[str, Any],
        policy_name: str,
        metric: str,
        value: float,
    ) -> bool:
        assert self.endpoint is not None  # for type checkers
        async with session.post(self.endpoint, json=payload, headers=headers) as response:
            if response.status in (200, 201):
                logger.info(f"Alert sent: {policy_name} ({metric} = {value})")
                return True
            error_text = await response.text()
            logger.warning(
                f"Failed to send alert to {self.endpoint}: {response.status} - {error_text}"
            )
            return False

    async def shutdown(self) -> None:
        """Shutdown alert client."""
        if self._session and not self._session.closed:
            await self._session.close()


# Global alert manager
_alert_manager: Any | None = None


def get_alert_client() -> AlertClient | None:
    """Get or create global alert client instance."""
    global _alert_client
    if _alert_client is None:
        endpoint = os.getenv("ALERTING_ENDPOINT")
        api_key = os.getenv("ALERTING_API_KEY")
        enabled = os.getenv("ALERTING_ENABLED", "false").lower() == "true"

        if enabled and endpoint:
            _alert_client = AlertClient(
                endpoint=endpoint,
                api_key=api_key,
                enabled=True,
            )
            logger.info(f"Alert client initialized for {endpoint}")
        else:
            logger.debug("Alerting not configured")

    return _alert_client


def get_slo_tracker() -> SLOTracker:
    """Get or create global SLO tracker instance."""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = {
            "slo_tracker": SLOTracker(
                availability_target=float(os.getenv("SLO_AVAILABILITY_TARGET", "0.99")),
                latency_p95_target_ms=float(os.getenv("SLO_LATENCY_P95_TARGET_MS", "1000.0")),
                error_rate_target=float(os.getenv("SLO_ERROR_RATE_TARGET", "0.01")),
            ),
            "policies": [],
        }
        logger.info("SLO tracker initialized")

    return _alert_manager["slo_tracker"]

