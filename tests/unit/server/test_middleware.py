import os
from unittest.mock import patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.cors import CORSMiddleware
from forge.server.middleware import LocalhostCORSMiddleware


@pytest.fixture
def app():
    """Create a test FastAPI application."""
    app = FastAPI()

    @app.get("/test")
    def test_endpoint():
        return {"message": "Test endpoint"}

    return app


def test_localhost_cors_middleware_init_with_env_var():
    """Test that the middleware correctly parses PERMITTED_CORS_ORIGINS environment variable."""
    with patch.dict(
        os.environ, {"PERMITTED_CORS_ORIGINS": "https://example.com,https://test.com"}
    ):
        app = FastAPI()
        middleware = LocalhostCORSMiddleware(app)
        assert "https://example.com" in middleware.allow_origins
        assert "https://test.com" in middleware.allow_origins
        assert len(middleware.allow_origins) == 2


def test_localhost_cors_middleware_init_without_env_var():
    """Test that the middleware works correctly without PERMITTED_CORS_ORIGINS environment variable."""
    with patch.dict(os.environ, {}, clear=True):
        app = FastAPI()
        middleware = LocalhostCORSMiddleware(app)
        assert middleware.allow_origins == ()


def test_localhost_cors_middleware_is_allowed_origin_localhost(app):
    """Test that localhost origins are allowed regardless of port when no specific origins are configured."""
    with patch.dict(os.environ, {}, clear=True):
        app.add_middleware(LocalhostCORSMiddleware)
        with TestClient(app) as client:
            response = client.get("/test", headers={"Origin": "http://localhost:8000"})
            assert response.status_code == 200
            assert (
                response.headers["access-control-allow-origin"]
                == "http://localhost:8000"
            )
            response = client.get("/test", headers={"Origin": "http://localhost:3000"})
            assert response.status_code == 200
            assert (
                response.headers["access-control-allow-origin"]
                == "http://localhost:3000"
            )
            response = client.get("/test", headers={"Origin": "http://127.0.0.1:8000"})
            assert response.status_code == 200
            assert (
                response.headers["access-control-allow-origin"]
                == "http://127.0.0.1:8000"
            )


def test_localhost_cors_middleware_is_allowed_origin_non_localhost(app):
    """Test that non-localhost origins follow the standard CORS rules."""
    with patch.dict(os.environ, {"PERMITTED_CORS_ORIGINS": "https://example.com"}):
        app.add_middleware(LocalhostCORSMiddleware)
        with TestClient(app) as client:
            response = client.get("/test", headers={"Origin": "https://example.com"})
            assert response.status_code == 200
            assert (
                response.headers["access-control-allow-origin"] == "https://example.com"
            )
            response = client.get("/test", headers={"Origin": "https://disallowed.com"})
            assert response.status_code == 200
            assert "access-control-allow-origin" not in response.headers


def test_localhost_cors_middleware_missing_origin(app):
    """Test behavior when Origin header is missing."""
    with patch.dict(os.environ, {}, clear=True):
        app.add_middleware(LocalhostCORSMiddleware)
        with TestClient(app) as client:
            response = client.get("/test")
            assert response.status_code == 200
            assert "access-control-allow-origin" not in response.headers


def test_localhost_cors_middleware_inheritance():
    """Test that LocalhostCORSMiddleware correctly inherits from CORSMiddleware."""
    assert issubclass(LocalhostCORSMiddleware, CORSMiddleware)


def test_localhost_cors_middleware_cors_parameters():
    """Test that CORS parameters are set correctly in the middleware."""
    with patch("fastapi.middleware.cors.CORSMiddleware.__init__") as mock_init:
        mock_init.return_value = None
        app = FastAPI()
        LocalhostCORSMiddleware(app)
        mock_init.assert_called_once()
        _, kwargs = mock_init.call_args
        assert kwargs["allow_credentials"] is True
        assert kwargs["allow_methods"] == ["*"]
        assert kwargs["allow_headers"] == ["*"]
