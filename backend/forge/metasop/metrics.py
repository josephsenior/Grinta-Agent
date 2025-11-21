"""Lightweight in-process metrics aggregation for MetaSOP events.

This avoids introducing external dependencies while providing a stable
facade that can later be swapped with Prometheus or OpenTelemetry.
"""

from __future__ import annotations

import contextlib
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Lock
from typing import Any


@dataclass
class _MetricState:
    """Internal state for metrics aggregation."""

    total_events: int = 0
    status_counts: dict[str, int] = field(default_factory=dict)
    steps_executed: int = 0
    steps_failed: int = 0
    steps_timed_out: int = 0
    suppressed_errors: int = 0
    total_tokens: int = 0
    model_token_totals: dict[str, int] = field(default_factory=dict)
    step_duration_buckets: dict[str, int] = field(default_factory=dict)
    step_duration_sum_ms: int = 0
    step_duration_count: int = 0
    step_duration_role_buckets: dict[str, dict[str, int]] = field(default_factory=dict)
    step_duration_role_sum_ms: dict[str, int] = field(default_factory=dict)
    step_duration_role_count: dict[str, int] = field(default_factory=dict)
    context_unique: int = 0
    context_reuse_total: int = 0
    _context_hashes: set[str] = field(default_factory=set)
    diff_unique: int = 0
    diff_reuse_total: int = 0
    _diff_fingerprints: set[str] = field(default_factory=set)
    __test__ = False
    micro_iter_events: int = 0
    micro_iter_no_change_stops: int = 0
    micro_iter_loops_converged: int = 0
    micro_iter_loops_exhausted: int = 0
    cache_hits: int = 0
    cache_stores: int = 0
    cache_entries: int = 0
    cache_evictions: int = 0
    retry_attempts: int = 0
    retry_failures: int = 0
    retry_successes: int = 0
    retry_attempts_by_op: dict[str, int] = field(default_factory=dict)
    retry_failures_by_op: dict[str, int] = field(default_factory=dict)
    retry_successes_by_op: dict[str, int] = field(default_factory=dict)
    guardrail_concurrency_events: int = 0
    guardrail_concurrency_last_active: int = 0
    guardrail_concurrency_last_limit: int = 0
    guardrail_concurrency_peak_active: int = 0
    guardrail_runtime_events: int = 0
    guardrail_runtime_sum_ms: int = 0
    guardrail_runtime_max_ms: int = 0
    guardrail_runtime_failures: int = 0


MetricsState = _MetricState


class MetricsRegistry:
    """Registry for aggregating MetaSOP orchestration metrics.

    Collects metrics on step execution, token usage, cache performance,
    retries, and micro-iteration convergence.
    """

    def __init__(self) -> None:
        """Initialize metrics registry with empty state."""
        self._state = _MetricState()
        self._lock = Lock()

    __test__ = False

    def _update_status_metrics(self, status: str) -> None:
        """Update status-specific metrics."""
        st = self._state
        if status in {"executed", "executed_shaped", "executed_cached"}:
            st.steps_executed += 1
        if status == "failed":
            st.steps_failed += 1
        elif status == "suppressed_error":
            st.suppressed_errors += 1
        elif status == "timeout":
            st.steps_timed_out += 1

    def _update_token_metrics(self, ev: dict[str, Any]) -> None:
        """Update token usage metrics."""
        st = self._state
        tokens = ev.get("total_tokens")
        if isinstance(tokens, int):
            st.total_tokens += tokens
            if model := (ev.get("model") or ev.get("model_name")):
                st.model_token_totals[model] = (
                    st.model_token_totals.get(model, 0) + tokens
                )

    def _update_latency_metrics(self, ev: dict[str, Any], role: str | None) -> None:
        """Update latency histograms for step durations."""
        dur = ev.get("duration_ms")
        if (
            isinstance(dur, int)
            and dur >= 0
            and (
                ev.get("status") in {"executed", "executed_shaped", "failed", "timeout"}
            )
        ):
            st = self._state
            st.step_duration_sum_ms += dur
            st.step_duration_count += 1
            if role:
                role_key = f"{role}_duration_sum_ms"
                if role_key not in st.step_duration_role_sum_ms:
                    st.step_duration_role_sum_ms[role_key] = 0
                st.step_duration_role_sum_ms[role_key] += dur
                role_count_key = f"{role}_duration_count"
                if role_count_key not in st.step_duration_role_count:
                    st.step_duration_role_count[role_count_key] = 0
                st.step_duration_role_count[role_count_key] += 1
            bucket = self._get_bucket(dur)
            st.step_duration_buckets[bucket] = (
                st.step_duration_buckets.get(bucket, 0) + 1
            )
            role_bucket_key = f"{role}_{bucket}" if role else bucket
            if role_bucket_key not in st.step_duration_role_buckets:
                st.step_duration_role_buckets[role_bucket_key] = {}
            st.step_duration_role_buckets[role_bucket_key][bucket] = (
                st.step_duration_role_buckets[role_bucket_key].get(bucket, 0) + 1
            )

    def _update_cache_metrics(self, ev: dict[str, Any]) -> None:
        """Update cache hit/store metrics."""
        st = self._state
        if ev.get("cache_hit"):
            st.cache_hits += 1
        if ev.get("cache_store"):
            st.cache_stores += 1
        st.cache_entries = ev.get("cache_entries", st.cache_entries)

    def _update_retry_metrics(self, ev: dict[str, Any]) -> None:
        """Update retry and operation-specific metrics."""
        st = self._state
        raw_retries = ev.get("retries")
        retries = 0
        if isinstance(raw_retries, bool):
            retries = int(raw_retries)
        elif isinstance(raw_retries, (int, float)):
            retries = int(raw_retries)
        elif isinstance(raw_retries, str):
            try:
                retries = int(raw_retries)
            except ValueError:
                retries = 0
        if retries > 0:
            st.retry_attempts += 1
            op = ev.get("operation", "unknown")
            st.retry_attempts_by_op[op] = st.retry_attempts_by_op.get(op, 0) + 1
            if ev.get("status") == "failed":
                st.retry_failures += 1
                st.retry_failures_by_op[op] = st.retry_failures_by_op.get(op, 0) + 1
            else:
                st.retry_successes += 1
                st.retry_successes_by_op[op] = st.retry_successes_by_op.get(op, 0) + 1

    def _get_bucket(self, duration_ms: int) -> str:
        """Get the latency bucket for the duration."""
        buckets = [0, 50, 100, 250, 500, 1000, 2000, 5000, 10000, float("inf")]
        return next(
            (f"le_{bucket}" for bucket in buckets if duration_ms <= bucket), "le_inf"
        )

    def _update_guardrail_concurrency(self, ev: dict[str, Any]) -> None:
        st = self._state
        active = ev.get("active_steps")
        limit = ev.get("limit")
        if isinstance(active, int):
            st.guardrail_concurrency_last_active = active
            st.guardrail_concurrency_peak_active = max(
                st.guardrail_concurrency_peak_active, active
            )
        if isinstance(limit, int):
            st.guardrail_concurrency_last_limit = limit
        st.guardrail_concurrency_events += 1

    def _update_guardrail_runtime(self, ev: dict[str, Any]) -> None:
        st = self._state
        duration = ev.get("duration_ms")
        if isinstance(duration, int) and duration >= 0:
            st.guardrail_runtime_sum_ms += duration
            st.guardrail_runtime_max_ms = max(
                st.guardrail_runtime_max_ms, duration
            )
        success = ev.get("success")
        if success is False:
            st.guardrail_runtime_failures += 1
        st.guardrail_runtime_events += 1

    def record_event(self, ev: dict[str, Any]) -> None:
        """Record an event to the metrics registry."""
        with self._lock:
            state = self._state
            self._increment_basic_counters(state, ev)

            event_type = ev.get("type")
            if self._handle_special_event(event_type, ev):
                return

            self._update_status_metrics(ev.get("status") or event_type or "unknown")
            self._update_token_metrics(ev)
            self._update_latency_metrics(ev, ev.get("role"))
            self._update_cache_metrics(ev)
            self._update_retry_metrics(ev)
            self._update_reuse_metrics(state, ev)
            self._update_micro_iter_metrics(state, ev)

    def _increment_basic_counters(self, state: MetricsState, ev: dict[str, Any]) -> None:
        state.total_events += 1
        status = ev.get("status") or ev.get("type") or "unknown"
        state.status_counts[status] = state.status_counts.get(status, 0) + 1

    def _handle_special_event(self, event_type: str | None, ev: dict[str, Any]) -> bool:
        if event_type == "guardrail_concurrency":
            self._update_guardrail_concurrency(ev)
            return True
        if event_type == "step_runtime_metrics":
            self._update_guardrail_runtime(ev)
            return True
        return False

    def _update_reuse_metrics(self, state: MetricsState, ev: dict[str, Any]) -> None:
        if ev.get("reason") == "cache_hit" or ev.get("cache_hit"):
            state.context_reuse_total += 1
        else:
            state.context_unique += 1

        if ev.get("reason") == "diff_reuse" or ev.get("diff_fingerprint_reuse"):
            state.diff_reuse_total += 1
        else:
            state.diff_unique += 1

    def _update_micro_iter_metrics(self, state: MetricsState, ev: dict[str, Any]) -> None:
        reason = ev.get("reason")
        if reason == "micro_iter_no_change":
            state.micro_iter_no_change_stops += 1
        elif reason == "micro_iter_loop_converged":
            state.micro_iter_loops_converged += 1
        elif reason == "micro_iter_loop_exhausted":
            state.micro_iter_loops_exhausted += 1
        if ev.get("micro_iter"):
            state.micro_iter_events += 1

    def snapshot(self) -> dict[str, Any]:
        """Get current metrics snapshot.

        Returns:
            Dictionary with aggregated metrics including events, tokens, latencies, cache stats

        """
        with self._lock:
            st = self._state

            def _percentiles(buckets: dict[str, int]) -> dict[str, float] | None:
                if not buckets:
                    return None
                ordered_bounds = sorted(
                    [
                        int(k.split("_")[1])
                        for k in buckets
                        if k.startswith("le_")
                        and k not in {"le_inf"}
                        and k.split("_")[1].isdigit()
                    ],
                )
                total = 0
                cumulative_map = {}
                running = 0
                for b in ordered_bounds:
                    running += buckets.get(f"le_{b}", 0)
                    cumulative_map[b] = running
                running += buckets.get("le_inf", 0)
                total = running
                if total == 0:
                    return None
                targets = {
                    "p50": 0.5 * total,
                    "p90": 0.9 * total,
                    "p95": 0.95 * total,
                    "p99": 0.99 * total,
                }
                out: dict[str, float] = {}
                for label, threshold in targets.items():
                    estimate = None
                    for b in ordered_bounds:
                        if cumulative_map[b] >= threshold:
                            estimate = float(b)
                            break
                    if estimate is None:
                        estimate = float(ordered_bounds[-1]) if ordered_bounds else 0.0
                    out[label] = estimate
                return out

            overall_hist = _percentiles(st.step_duration_buckets)
            return {
                "rationale": "Operational metrics for retries, latencies, cache and token usage to aid reliability and debugging.",
                "total_events": st.total_events,
                "status_counts": dict(st.status_counts),
                "steps_executed": st.steps_executed,
                "steps_failed": st.steps_failed,
                "steps_timed_out": st.steps_timed_out,
                "suppressed_errors": st.suppressed_errors,
                "total_tokens": st.total_tokens,
                "model_token_totals": dict(st.model_token_totals),
                "avg_tokens_per_executed_step": st.total_tokens / st.steps_executed
                if st.steps_executed
                else None,
                "step_duration_histogram": {
                    "buckets": dict(st.step_duration_buckets),
                    "sum_ms": st.step_duration_sum_ms,
                    "count": st.step_duration_count,
                    **({"percentiles": overall_hist} if overall_hist else {}),
                },
                "step_duration_histogram_by_role": {
                    role: {
                        "buckets": dict(buckets),
                        "sum_ms": st.step_duration_role_sum_ms.get(role, 0),
                        "count": st.step_duration_role_count.get(role, 0),
                        **(
                            {"percentiles": _percentiles(buckets)}
                            if _percentiles(buckets)
                            else {}
                        ),
                    }
                    for role, buckets in st.step_duration_role_buckets.items()
                },
                "context_unique": st.context_unique,
                "context_reuse_total": st.context_reuse_total,
                "diff_unique": st.diff_unique,
                "diff_reuse_total": st.diff_reuse_total,
                "micro_iter_events": st.micro_iter_events,
                "micro_iter_no_change_stops": st.micro_iter_no_change_stops,
                "micro_iter_loops_converged": st.micro_iter_loops_converged,
                "micro_iter_loops_exhausted": st.micro_iter_loops_exhausted,
                "cache_hits": st.cache_hits,
                "cache_stores": st.cache_stores,
                "cache_entries": st.cache_entries,
                "cache_evictions": st.cache_evictions,
                "retry_attempts": st.retry_attempts,
                "retry_failures": st.retry_failures,
                "retry_successes": st.retry_successes,
                "retry_attempts_by_operation": dict(st.retry_attempts_by_op),
                "retry_failures_by_operation": dict(st.retry_failures_by_op),
                "retry_successes_by_operation": dict(st.retry_successes_by_op),
                "guardrail_concurrency_events": st.guardrail_concurrency_events,
                "guardrail_concurrency_last_active": st.guardrail_concurrency_last_active,
                "guardrail_concurrency_last_limit": st.guardrail_concurrency_last_limit,
                "guardrail_concurrency_peak_active": st.guardrail_concurrency_peak_active,
                "guardrail_runtime_events": st.guardrail_runtime_events,
                "guardrail_runtime_avg_ms": (
                    st.guardrail_runtime_sum_ms / st.guardrail_runtime_events
                    if st.guardrail_runtime_events
                    else None
                ),
                "guardrail_runtime_max_ms": st.guardrail_runtime_max_ms,
                "guardrail_runtime_failures": st.guardrail_runtime_failures,
                "rationale_note": "Operational metrics for retries, latencies, cache and token usage to aid reliability and debugging.",
            }


_GLOBAL_REGISTRY: MetricsRegistry | None = None


def get_metrics_registry() -> MetricsRegistry:
    """Return global MetricsRegistry singleton (creating if needed)."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = MetricsRegistry()
    return _GLOBAL_REGISTRY


def record_event(ev: dict[str, Any]) -> None:
    """Record an orchestration event into the shared metrics registry."""
    with contextlib.suppress(Exception):
        get_metrics_registry().record_event(ev)


__all__ = ["get_metrics_registry", "record_event"]
_METRICS_SERVER: HTTPServer | None = None


class _MetricsHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Prometheus metrics endpoint."""

    def _build_basic_metrics(self, snap: dict) -> list[str]:
        """Build basic metrics lines from snapshot.

        Args:
            snap: Metrics snapshot dictionary

        Returns:
            List of Prometheus metric lines

        """
        body_lines: list[str] = [
            "# HELP metasop_total_events Total events observed",
            "# TYPE metasop_total_events counter",
            f"metasop_total_events {snap['total_events']}",
        ]
        for status, count in snap["status_counts"].items():
            body_lines.extend(
                (
                    "# TYPE metasop_status_count counter",
                    f'metasop_status_count{{status="{status}"}} {count}',
                ),
            )
        return body_lines

    def _build_token_metrics(self, snap: dict) -> list[str]:
        """Build token-related metrics lines from snapshot.

        Args:
            snap: Metrics snapshot dictionary

        Returns:
            List of Prometheus metric lines for token usage

        """
        body_lines: list[str] = []
        if snap["avg_tokens_per_executed_step"] is not None:
            body_lines.extend(
                (
                    "# TYPE metasop_avg_tokens_per_executed_step gauge",
                    f"metasop_avg_tokens_per_executed_step {snap['avg_tokens_per_executed_step']}",
                ),
            )
        body_lines.extend(
            (
                "# TYPE metasop_total_tokens counter",
                f"metasop_total_tokens {snap['total_tokens']}",
            )
        )
        for model, tok in snap["model_token_totals"].items():
            body_lines.extend(
                (
                    "# TYPE metasop_model_total_tokens counter",
                    f'metasop_model_total_tokens{{model="{model}"}} {tok}',
                ),
            )
        return body_lines

    def _build_histogram_metrics(self, snap: dict) -> list[str]:
        """Build histogram metrics lines from snapshot.

        Args:
            snap: Metrics snapshot dictionary

        Returns:
            List of metric lines

        """
        hist = snap.get("step_duration_histogram") or {}
        buckets = hist.get("buckets", {})

        if not buckets:
            return []

        body_lines: list[str] = [
            "# RATIONALE: Operational metrics to track retries, latencies, cache and token usage for reliability and debugging.",
            "# HELP metasop_step_duration_ms Step duration histogram (ms)",
            "# TYPE metasop_step_duration_ms histogram",
        ]

        body_lines.extend(self._build_histogram_buckets(buckets))
        body_lines.extend(self._build_histogram_summary(hist))
        body_lines.extend(self._build_histogram_percentiles(hist))

        return body_lines

    def _build_histogram_buckets(self, buckets: dict) -> list[str]:
        """Build histogram bucket lines.

        Args:
            buckets: Bucket data

        Returns:
            List of bucket metric lines

        """
        lines = []
        ordered_bounds = sorted(
            [
                int(k.split("_")[1])
                for k in buckets
                if k.startswith("le_")
                and k not in {"le_inf"}
                and k.split("_")[1].isdigit()
            ],
        )

        cumulative = 0
        for b in ordered_bounds:
            cumulative += buckets.get(f"le_{b}", 0)
            lines.append(f'metasop_step_duration_ms_bucket{{le="{b}"}} {cumulative}')

        cumulative += buckets.get("le_inf", 0)
        lines.append(f'metasop_step_duration_ms_bucket{{le="+Inf"}} {cumulative}')

        return lines

    def _build_histogram_summary(self, hist: dict) -> list[str]:
        """Build histogram summary lines.

        Args:
            hist: Histogram data

        Returns:
            List of summary metric lines

        """
        return [
            f"metasop_step_duration_ms_sum {hist.get('sum_ms', 0)}",
            f"metasop_step_duration_ms_count {hist.get('count', 0)}",
        ]

    def _build_histogram_percentiles(self, hist: dict) -> list[str]:
        """Build histogram percentile lines.

        Args:
            hist: Histogram data

        Returns:
            List of percentile metric lines

        """
        pct = hist.get("percentiles") or {}
        return [
            f"metasop_step_duration_ms_{label} {pct[label]}"
            for label in ["p50", "p90", "p95", "p99"]
            if label in pct
        ]

    def _build_role_histogram_metrics(self, snap: dict) -> list[str]:
        """Build per-role histogram metrics lines from snapshot.

        Args:
            snap: Metrics snapshot dictionary

        Returns:
            List of metric lines

        """
        body_lines: list[str] = []
        role_hists = snap.get("step_duration_histogram_by_role") or {}

        for role, meta in role_hists.items():
            rbuckets = meta.get("buckets", {})
            if not rbuckets:
                continue

            body_lines.extend(self._build_single_role_histogram(role, rbuckets, meta))

        return body_lines

    def _build_single_role_histogram(
        self, role: str, rbuckets: dict, meta: dict
    ) -> list[str]:
        """Build histogram metrics for a single role.

        Args:
            role: Role name
            rbuckets: Bucket data for role
            meta: Metadata for role

        Returns:
            List of metric lines for this role

        """
        lines = ["# TYPE metasop_step_duration_ms_role histogram"]

        ordered_bounds = sorted(
            [
                int(k.split("_")[1])
                for k in rbuckets
                if k.startswith("le_")
                and k not in {"le_inf"}
                and k.split("_")[1].isdigit()
            ],
        )

        cumulative = 0
        for b in ordered_bounds:
            cumulative += rbuckets.get(f"le_{b}", 0)
            lines.append(
                f'metasop_step_duration_ms_role_bucket{{role="{role}",le="{b}"}} {cumulative}'
            )

        cumulative += rbuckets.get("le_inf", 0)
        lines.extend(
            [
                f'metasop_step_duration_ms_role_bucket{{role="{role}",le="+Inf"}} {cumulative}',
                f'metasop_step_duration_ms_role_sum{{role="{role}"}} {meta.get("sum_ms", 0)}',
                f'metasop_step_duration_ms_role_count{{role="{role}"}} {meta.get("count", 0)}',
            ],
        )

        rpct = meta.get("percentiles") or {}
        lines.extend(
            [
                f'metasop_step_duration_ms_role_{label}{{role="{role}"}} {rpct[label]}'
                for label in ["p50", "p90", "p95", "p99"]
                if label in rpct
            ],
        )

        return lines

    def _build_additional_metrics(self, snap: dict) -> list[str]:
        """Build additional metrics lines from snapshot."""
        body_lines: list[str] = [
            "# TYPE metasop_context_unique gauge",
            f"metasop_context_unique {snap.get('context_unique', 0)}",
            "# TYPE metasop_context_reuse_total counter",
            f"metasop_context_reuse_total {snap.get('context_reuse_total', 0)}",
            "# TYPE metasop_diff_unique gauge",
            f"metasop_diff_unique {snap.get('diff_unique', 0)}",
            "# TYPE metasop_diff_reuse_total counter",
            f"metasop_diff_reuse_total {snap.get('diff_reuse_total', 0)}",
            "# TYPE metasop_micro_iter_events counter",
            f"metasop_micro_iter_events {snap.get('micro_iter_events', 0)}",
            "# TYPE metasop_micro_iter_no_change_stops counter",
            f"metasop_micro_iter_no_change_stops {snap.get('micro_iter_no_change_stops', 0)}",
            "# TYPE metasop_micro_iter_loops_converged counter",
            f"metasop_micro_iter_loops_converged {snap.get('micro_iter_loops_converged', 0)}",
        ]
        body_lines.append("# TYPE metasop_micro_iter_loops_exhausted counter")
        body_lines.append(
            f"metasop_micro_iter_loops_exhausted {snap.get('micro_iter_loops_exhausted', 0)}"
        )
        body_lines.append("# TYPE metasop_cache_hits counter")
        body_lines.append(f"metasop_cache_hits {snap.get('cache_hits', 0)}")
        body_lines.append("# TYPE metasop_cache_stores counter")
        body_lines.append(f"metasop_cache_stores {snap.get('cache_stores', 0)}")
        body_lines.append("# TYPE metasop_cache_entries gauge")
        body_lines.append(f"metasop_cache_entries {snap.get('cache_entries', 0)}")
        body_lines.append("# TYPE metasop_cache_evictions counter")
        body_lines.append(f"metasop_cache_evictions {snap.get('cache_evictions', 0)}")
        body_lines.append("# TYPE metasop_retry_attempts counter")
        body_lines.append(f"metasop_retry_attempts {snap.get('retry_attempts', 0)}")
        body_lines.extend(
            [
                "# TYPE metasop_guardrail_concurrency_total counter",
                f"metasop_guardrail_concurrency_total {snap.get('guardrail_concurrency_events', 0)}",
                "# TYPE metasop_guardrail_concurrency_peak gauge",
                f"metasop_guardrail_concurrency_peak {snap.get('guardrail_concurrency_peak_active', 0)}",
                "# TYPE metasop_guardrail_concurrency_last_active gauge",
                f"metasop_guardrail_concurrency_last_active {snap.get('guardrail_concurrency_last_active', 0)}",
                "# TYPE metasop_guardrail_concurrency_last_limit gauge",
                f"metasop_guardrail_concurrency_last_limit {snap.get('guardrail_concurrency_last_limit', 0)}",
            ]
        )
        avg_runtime = snap.get("guardrail_runtime_avg_ms")
        if avg_runtime is not None:
            body_lines.append("# TYPE metasop_guardrail_runtime_avg_ms gauge")
            body_lines.append(f"metasop_guardrail_runtime_avg_ms {avg_runtime}")
        body_lines.extend(
            [
                "# TYPE metasop_guardrail_runtime_max_ms gauge",
                f"metasop_guardrail_runtime_max_ms {snap.get('guardrail_runtime_max_ms', 0)}",
                "# TYPE metasop_guardrail_runtime_events counter",
                f"metasop_guardrail_runtime_events {snap.get('guardrail_runtime_events', 0)}",
                "# TYPE metasop_guardrail_runtime_failures counter",
                f"metasop_guardrail_runtime_failures {snap.get('guardrail_runtime_failures', 0)}",
            ]
        )
        return body_lines

    def do_GET(self) -> None:
        """Handle GET requests to /metrics endpoint."""
        if self.path != "/metrics":
            self.send_response(404)
            self.end_headers()
            return
        snap = get_metrics_registry().snapshot()
        body_lines: list[str] = []
        body_lines.extend(self._build_basic_metrics(snap))
        body_lines.extend(self._build_token_metrics(snap))
        body_lines.extend(self._build_histogram_metrics(snap))
        body_lines.extend(self._build_role_histogram_metrics(snap))
        body_lines.extend(self._build_additional_metrics(snap))
        body = "\n".join(body_lines) + "\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body.encode("utf-8"))))
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args) -> None:
        """Silence BaseHTTPRequestHandler default logging."""
        return


def start_metrics_server(port: int) -> bool:
    """Start a background HTTP server exposing /metrics in Prometheus text format.

    Returns True if started, False if already running or failed.
    """
    global _METRICS_SERVER
    if _METRICS_SERVER is not None:
        return False
    try:
        server = HTTPServer(
            ("0.0.0.0", port),
            _MetricsHandler,
        )  # nosec B104 - Safe: metrics server intentionally accessible
    except Exception:
        return False

    def _serve() -> None:
        with contextlib.suppress(Exception):
            server.serve_forever()

    th = threading.Thread(target=_serve, daemon=True)
    th.start()
    _METRICS_SERVER = server
    return True


__all__.append("start_metrics_server")
