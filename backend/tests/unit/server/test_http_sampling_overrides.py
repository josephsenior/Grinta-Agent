import importlib
import os
import sys
from types import ModuleType

# Ensure repository root is on path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def reload_app_with_env(env: dict[str, str]) -> ModuleType:
    # Clean up any prior import to re-evaluate env parsing
    if "forge.server.app" in sys.modules:
        del sys.modules["forge.server.app"]
    # Apply env
    for k in list(os.environ.keys()):
        if (
            k.startswith("OTEL_SAMPLE_HTTP")
            or k.startswith("OTEL_SAMPLE_ROUTES")
            or k.startswith("OTEL_SAMPLE_DEFAULT")
        ):
            os.environ.pop(k, None)
    os.environ.update(env)
    # Import target
    app_module = importlib.import_module("forge.server.app")
    return app_module


def test_parser_accepts_exact_and_prefix_patterns():
    app_module = reload_app_with_env(
        {
            "OTEL_ENABLED": "true",
            "OTEL_SAMPLE_DEFAULT": "0.25",
            "OTEL_SAMPLE_HTTP": "0.1",
            "OTEL_SAMPLE_ROUTES": "/api/conversations*:1.0;/api/files:0.2;/health:1.0",
        }
    )
    # Sanity: helper exists
    assert hasattr(app_module, "get_effective_http_sample")

    eff = app_module.get_effective_http_sample("/api/conversations/abc")
    assert eff == 1.0

    eff = app_module.get_effective_http_sample("/api/files")
    assert eff == 0.2

    eff = app_module.get_effective_http_sample("/health")
    assert eff == 1.0


def test_parser_fallback_to_http_then_default():
    # First case: routes unset -> falls back to HTTP value
    app_module = reload_app_with_env(
        {
            "OTEL_ENABLED": "true",
            "OTEL_SAMPLE_DEFAULT": "0.9",
            "OTEL_SAMPLE_HTTP": "0.15",
            # No OTEL_SAMPLE_ROUTES
        }
    )
    eff = app_module.get_effective_http_sample("/api/unknown")
    assert eff == 0.15

    # Second case: HTTP unset -> falls back to DEFAULT
    app_module = reload_app_with_env(
        {
            "OTEL_ENABLED": "true",
            "OTEL_SAMPLE_DEFAULT": "0.33",
            # No OTEL_SAMPLE_HTTP
        }
    )
    eff = app_module.get_effective_http_sample("/api/unknown")
    assert eff == 0.33


def test_first_match_wins_ordering():
    app_module = reload_app_with_env(
        {
            "OTEL_ENABLED": "true",
            "OTEL_SAMPLE_DEFAULT": "1.0",
            "OTEL_SAMPLE_HTTP": "0.05",
            "OTEL_SAMPLE_ROUTES": "/api/conversations*:1.0;/api/conversations:0.1",
        }
    )
    # Because of left-to-right, the prefix rule is first -> wins
    eff = app_module.get_effective_http_sample("/api/conversations")
    assert eff == 1.0


def test_invalid_entries_are_ignored():
    app_module = reload_app_with_env(
        {
            "OTEL_ENABLED": "true",
            "OTEL_SAMPLE_DEFAULT": "0.8",
            "OTEL_SAMPLE_HTTP": "0.4",
            "OTEL_SAMPLE_ROUTES": ";;;/api/bad;no_colon; /api/good*:not_a_number; /api/ok:0.7 ",
        }
    )
    # bad entries ignored; invalid number falls back to 1.0 (then clamped)
    # first valid that matches should be /api/ok:0.7 when requesting /api/ok
    eff = app_module.get_effective_http_sample("/api/ok")
    assert eff == 0.7

    # For a non-matching route, fallback to HTTP value (0.4)
    eff = app_module.get_effective_http_sample("/api/none")
    assert eff == 0.4
