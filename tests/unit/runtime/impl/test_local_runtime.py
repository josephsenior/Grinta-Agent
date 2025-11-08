"""Unit tests for LocalRuntime's URL-related methods."""

import os
from unittest.mock import MagicMock, patch
import pytest
from forge.core.config import ForgeConfig
from forge.events import EventStream
from forge.runtime.impl.local.local_runtime import LocalRuntime


@pytest.fixture
def config():
    """Create a mock ForgeConfig for testing."""
    config = ForgeConfig()
    config.sandbox.local_runtime_url = "http://localhost"
    config.workspace_mount_path_in_sandbox = "/workspace"
    return config


@pytest.fixture
def event_stream():
    """Create a mock EventStream for testing."""
    return MagicMock(spec=EventStream)


@pytest.fixture
def local_runtime(config, event_stream):
    """Create a LocalRuntime instance for testing."""
    runtime = LocalRuntime.__new__(LocalRuntime)
    runtime.config = config
    runtime.event_stream = event_stream
    runtime._vscode_port = 8080
    runtime._app_ports = [12000, 12001]
    runtime._runtime_initialized = True
    runtime._vscode_enabled = True
    runtime._vscode_token = "test-token"

    def mock_runtime_url(self):
        return "http://localhost"

    type(runtime).runtime_url = property(mock_runtime_url)
    return runtime


class TestLocalRuntime:
    """Tests for LocalRuntime's URL-related methods."""

    def test_runtime_url_with_env_var(self):
        """Test runtime_url when RUNTIME_URL environment variable is set."""
        config = ForgeConfig()
        config.sandbox.local_runtime_url = "http://localhost"
        runtime = LocalRuntime.__new__(LocalRuntime)
        runtime.config = config
        with patch.dict(os.environ, {"RUNTIME_URL": "http://custom-url"}, clear=True):
            original_property = LocalRuntime.runtime_url
            try:
                assert original_property.__get__(runtime) == "http://custom-url"
            finally:
                LocalRuntime.runtime_url = original_property

    def test_runtime_url_with_pattern(self):
        """Test runtime_url when RUNTIME_URL_PATTERN environment variable is set."""
        config = ForgeConfig()
        config.sandbox.local_runtime_url = "http://localhost"
        runtime = LocalRuntime.__new__(LocalRuntime)
        runtime.config = config
        env_vars = {"RUNTIME_URL_PATTERN": "http://runtime-{runtime_id}.example.com", "RUNTIME_ID": "abc123"}
        with patch.dict(os.environ, env_vars, clear=True):
            original_property = LocalRuntime.runtime_url
            try:
                assert original_property.__get__(runtime) == "http://runtime-abc123.example.com"
            finally:
                LocalRuntime.runtime_url = original_property

    def test_runtime_url_fallback(self):
        """Test runtime_url fallback to local_runtime_url."""
        config = ForgeConfig()
        config.sandbox.local_runtime_url = "http://localhost"
        runtime = LocalRuntime.__new__(LocalRuntime)
        runtime.config = config
        with patch.dict(os.environ, {}, clear=True):
            original_property = LocalRuntime.runtime_url
            try:
                assert original_property.__get__(runtime) == "http://localhost"
            finally:
                LocalRuntime.runtime_url = original_property

    def test_create_url_with_localhost(self):
        """Test _create_url when runtime_url contains 'localhost'."""
        config = ForgeConfig()
        runtime = LocalRuntime.__new__(LocalRuntime)
        runtime.config = config
        runtime._vscode_port = 8080

        def mock_runtime_url(self):
            return "http://localhost"

        original_property = LocalRuntime.runtime_url
        try:
            LocalRuntime.runtime_url = property(mock_runtime_url)
            url = runtime._create_url("test-prefix", 9000)
            assert url == "http://localhost:8080"
        finally:
            LocalRuntime.runtime_url = original_property

    def test_create_url_with_remote_url(self):
        """Test _create_url when runtime_url is a remote URL."""
        config = ForgeConfig()
        runtime = LocalRuntime.__new__(LocalRuntime)
        runtime.config = config

        def mock_runtime_url(self):
            return "https://example.com"

        original_property = LocalRuntime.runtime_url
        try:
            LocalRuntime.runtime_url = property(mock_runtime_url)
            url = runtime._create_url("test-prefix", 9000)
            assert url == "https://test-prefix-example.com"
        finally:
            LocalRuntime.runtime_url = original_property

    def test_vscode_url_with_token(self):
        """Test vscode_url when token is available."""
        config = ForgeConfig()
        config.workspace_mount_path_in_sandbox = "/workspace"
        runtime = LocalRuntime.__new__(LocalRuntime)
        runtime.config = config
        runtime._vscode_enabled = True
        runtime._runtime_initialized = True
        runtime._vscode_token = "test-token"

        def mock_vscode_url(self):
            token = "test-token"
            if not token:
                return None
            vscode_url = "https://vscode-example.com"
            return f"{vscode_url}/?tkn={token}&folder={self.config.workspace_mount_path_in_sandbox}"

        original_method = LocalRuntime.vscode_url
        try:
            LocalRuntime.vscode_url = property(mock_vscode_url)
            url = runtime.vscode_url
            assert url == "https://vscode-example.com/?tkn=test-token&folder=/workspace"
        finally:
            LocalRuntime.vscode_url = original_method

    def test_vscode_url_without_token(self):
        """Test vscode_url when token is not available."""
        config = ForgeConfig()
        runtime = LocalRuntime.__new__(LocalRuntime)
        runtime.config = config

        def mock_vscode_url(self):
            return None

        original_method = LocalRuntime.vscode_url
        try:
            LocalRuntime.vscode_url = property(mock_vscode_url)
            assert runtime.vscode_url is None
        finally:
            LocalRuntime.vscode_url = original_method

    def test_web_hosts_with_multiple_ports(self):
        """Test web_hosts with multiple app ports."""
        config = ForgeConfig()
        runtime = LocalRuntime.__new__(LocalRuntime)
        runtime.config = config
        runtime._app_ports = [12000, 12001]

        def mock_create_url(prefix, port):
            return f"https://{prefix}-example.com"

        with patch.object(runtime, "_create_url", side_effect=mock_create_url):
            hosts = runtime.web_hosts
            assert len(hosts) == 2
            assert "https://work-1-example.com" in hosts
            assert hosts["https://work-1-example.com"] == 12000
            assert "https://work-2-example.com" in hosts
            assert hosts["https://work-2-example.com"] == 12001

    def test_web_hosts_with_no_ports(self):
        """Test web_hosts with no app ports."""
        config = ForgeConfig()
        runtime = LocalRuntime.__new__(LocalRuntime)
        runtime.config = config
        runtime._app_ports = []
        hosts = runtime.web_hosts
        assert hosts == {}
