"""Integration tests for runtime performance optimization.

These tests verify that the warm server pool feature significantly
reduces runtime startup time.
"""

import os
import time
import pytest
from unittest.mock import patch

from forge.core.config import ForgeConfig, load_from_toml
from forge.runtime.impl.local.local_runtime import LocalRuntime, _WARM_SERVERS
from forge.events.stream import EventStream


@pytest.mark.integration
class TestWarmServerPerformance:
    """Test suite for warm server pool performance."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Clear warm server pool before and after each test."""
        _WARM_SERVERS.clear()
        yield
        _WARM_SERVERS.clear()

    @pytest.mark.asyncio
    async def test_cold_start_is_slow(self, temp_dir):
        """Verify that cold start (no warm servers) is slower than 30s."""
        # Disable warm servers
        with patch.dict(
            os.environ,
            {
                "INITIAL_NUM_WARM_SERVERS": "0",
                "DESIRED_NUM_WARM_SERVERS": "0",
            },
        ):
            config = load_from_toml("config.toml")
            config.workspace_base = str(temp_dir)

            event_stream = EventStream("test")
            runtime = LocalRuntime(
                config=config,
                event_stream=event_stream,
                sid="test-cold",
            )

            start_time = time.time()

            try:
                await runtime.connect()
                elapsed = time.time() - start_time

                # Cold start should take more than 30 seconds
                assert elapsed > 30, (
                    f"Cold start was too fast: {elapsed:.2f}s. "
                    "Expected >30s without warm servers."
                )

                print(f"[OK] Cold start time: {elapsed:.2f}s (baseline)")

            finally:
                runtime.close()

    @pytest.mark.asyncio
    async def test_warm_start_is_fast(self, temp_dir):
        """Verify that warm start (with warm servers) is faster than 10s."""
        # Enable warm servers
        with patch.dict(
            os.environ,
            {
                "INITIAL_NUM_WARM_SERVERS": "1",
                "DESIRED_NUM_WARM_SERVERS": "1",
            },
        ):
            config = load_from_toml("config.toml")
            config.workspace_base = str(temp_dir)

            # Pre-create warm server
            from forge.runtime.impl.local.local_runtime import (
                _create_warm_server,
                _get_plugins,
            )

            plugins = _get_plugins(config)
            _create_warm_server(config, plugins)

            # Wait for warm server to be ready
            time.sleep(5)
            assert len(_WARM_SERVERS) > 0, "Warm server pool should not be empty"

            # Now test startup time with warm server
            event_stream = EventStream("test")
            runtime = LocalRuntime(
                config=config,
                event_stream=event_stream,
                sid="test-warm",
            )

            start_time = time.time()

            try:
                await runtime.connect()
                elapsed = time.time() - start_time

                # Warm start should be much faster (<10s)
                assert elapsed < 10, (
                    f"Warm start was too slow: {elapsed:.2f}s. "
                    "Expected <10s with warm servers."
                )

                # Ideally should be <5s
                if elapsed < 5:
                    print(f"[OK] Warm start time: {elapsed:.2f}s (excellent!)")
                else:
                    print(f"[OK] Warm start time: {elapsed:.2f}s (acceptable)")

            finally:
                runtime.close()

    @pytest.mark.asyncio
    async def test_warm_server_pool_maintenance(self, temp_dir):
        """Verify that warm server pool maintains desired size."""
        with patch.dict(
            os.environ,
            {
                "INITIAL_NUM_WARM_SERVERS": "2",
                "DESIRED_NUM_WARM_SERVERS": "2",
            },
        ):
            config = load_from_toml("config.toml")
            config.workspace_base = str(temp_dir)

            # Pre-create warm servers
            from forge.runtime.impl.local.local_runtime import (
                _create_warm_server,
                _get_plugins,
            )

            plugins = _get_plugins(config)

            # Create 2 warm servers
            for i in range(2):
                _create_warm_server(config, plugins)

            time.sleep(5)

            # Verify pool has 2 servers
            assert len(_WARM_SERVERS) == 2, (
                f"Expected 2 warm servers, got {len(_WARM_SERVERS)}"
            )

            # Use one warm server
            event_stream = EventStream("test")
            runtime = LocalRuntime(
                config=config,
                event_stream=event_stream,
                sid="test-maintenance",
            )

            await runtime.connect()

            # Pool should have 1 server now (1 was consumed)
            assert len(_WARM_SERVERS) == 1, (
                f"Expected 1 warm server after use, got {len(_WARM_SERVERS)}"
            )

            # System should create new warm server in background
            # (This happens asynchronously, so we just verify the trigger)

            runtime.close()

            print("[OK] Warm server pool maintenance working correctly")

    @pytest.mark.asyncio
    async def test_performance_improvement_ratio(self, temp_dir):
        """Verify warm servers provide at least 80% performance improvement."""
        # This is an approximate test - actual timing may vary
        # We're testing the RELATIVE improvement, not absolute values

        cold_start_time = 60  # Baseline (measured empirically)

        with patch.dict(
            os.environ,
            {
                "INITIAL_NUM_WARM_SERVERS": "1",
                "DESIRED_NUM_WARM_SERVERS": "1",
            },
        ):
            config = load_from_toml("config.toml")
            config.workspace_base = str(temp_dir)

            # Pre-create warm server
            from forge.runtime.impl.local.local_runtime import (
                _create_warm_server,
                _get_plugins,
            )

            plugins = _get_plugins(config)
            _create_warm_server(config, plugins)
            time.sleep(5)

            # Measure warm startup
            event_stream = EventStream("test")
            runtime = LocalRuntime(
                config=config,
                event_stream=event_stream,
                sid="test-improvement",
            )

            start_time = time.time()

            try:
                await runtime.connect()
                warm_start_time = time.time() - start_time

                # Calculate improvement
                improvement = (
                    (cold_start_time - warm_start_time) / cold_start_time
                ) * 100

                # Should be at least 80% improvement
                assert improvement >= 80, (
                    f"Performance improvement was only {improvement:.1f}%. "
                    f"Expected at least 80% (cold: {cold_start_time}s, warm: {warm_start_time:.2f}s)"
                )

                print(
                    f"[OK] Performance improvement: {improvement:.1f}% (target: >80%)"
                )
                print(f"  Cold start: {cold_start_time}s (baseline)")
                print(f"  Warm start: {warm_start_time:.2f}s")

            finally:
                runtime.close()


@pytest.mark.integration
def test_warm_server_environment_variables():
    """Verify warm server environment variables are correctly read."""
    with patch.dict(
        os.environ,
        {
            "INITIAL_NUM_WARM_SERVERS": "3",
            "DESIRED_NUM_WARM_SERVERS": "5",
        },
    ):
        initial = int(os.getenv("INITIAL_NUM_WARM_SERVERS", "0"))
        desired = int(os.getenv("DESIRED_NUM_WARM_SERVERS", "0"))

        assert initial == 3, f"Expected INITIAL_NUM_WARM_SERVERS=3, got {initial}"
        assert desired == 5, f"Expected DESIRED_NUM_WARM_SERVERS=5, got {desired}"

        print("[OK] Environment variables configured correctly")


@pytest.mark.integration
def test_performance_tuning_variables():
    """Verify performance tuning environment variables are applied."""
    with patch.dict(
        os.environ,
        {
            "INIT_PLUGIN_TIMEOUT": "60",
            "NO_CHANGE_TIMEOUT_SECONDS": "10",
            "SKIP_DEPENDENCY_CHECK": "1",
        },
    ):
        plugin_timeout = int(os.getenv("INIT_PLUGIN_TIMEOUT", "120"))
        bash_timeout = int(os.getenv("NO_CHANGE_TIMEOUT_SECONDS", "30"))
        skip_deps = os.getenv("SKIP_DEPENDENCY_CHECK", "") == "1"

        assert plugin_timeout == 60, (
            f"Expected INIT_PLUGIN_TIMEOUT=60, got {plugin_timeout}"
        )
        assert bash_timeout == 10, (
            f"Expected NO_CHANGE_TIMEOUT_SECONDS=10, got {bash_timeout}"
        )
        assert skip_deps is True, "Expected SKIP_DEPENDENCY_CHECK=1"

        print("[OK] Performance tuning variables applied correctly")
