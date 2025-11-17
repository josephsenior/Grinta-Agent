import importlib
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def reload_app(env: dict[str, str]):
    for k in list(os.environ.keys()):
        if (
            k.startswith("OTEL_SAMPLE_HTTP")
            or k.startswith("OTEL_SAMPLE_ROUTES")
            or k.startswith("OTEL_SAMPLE_DEFAULT")
            or k.startswith("OTEL_SAMPLE_ROUTES_REGEX")
        ):
            os.environ.pop(k, None)
    os.environ.update(env)
    if "forge.server.app" in sys.modules:
        del sys.modules["forge.server.app"]
    return importlib.import_module("forge.server.app")


def test_regex_precedence_over_simple_rules():
    m = reload_app(
        {
            "OTEL_ENABLED": "true",
            "OTEL_SAMPLE_DEFAULT": "0.5",
            "OTEL_SAMPLE_HTTP": "0.2",
            "OTEL_SAMPLE_ROUTES": "/api/conversations*:0.1",
            "OTEL_SAMPLE_ROUTES_REGEX": "^/api/conversations/.*:1.0",
        }
    )
    # Regex should win
    assert m.get_effective_http_sample("/api/conversations/xyz") == 1.0
    # Non-matching regex falls back to simple prefix rule
    assert m.get_effective_http_sample("/api/conversations") == 0.1


def test_multiple_regex_first_match_wins():
    m = reload_app(
        {
            "OTEL_ENABLED": "true",
            "OTEL_SAMPLE_HTTP": "0.05",
            "OTEL_SAMPLE_ROUTES_REGEX": "^/api/.*:0.4;^/api/conversations.*:0.9",
        }
    )
    # First regex matches and should take precedence even though later is more specific
    assert m.get_effective_http_sample("/api/conversations/123") == 0.4


def test_regex_fallback_to_simple_then_http():
    m = reload_app(
        {
            "OTEL_ENABLED": "true",
            "OTEL_SAMPLE_HTTP": "0.15",
            "OTEL_SAMPLE_ROUTES": "/api/files:0.7",
            "OTEL_SAMPLE_ROUTES_REGEX": "^/private/.*:0.0",
        }
    )
    # Regex doesn't match; simple route match used
    assert m.get_effective_http_sample("/api/files") == 0.7
    # Neither regex nor simple rules match -> fall back to HTTP base
    assert m.get_effective_http_sample("/misc") == 0.15


def test_invalid_regex_safely_ignored():
    m = reload_app(
        {
            "OTEL_ENABLED": "true",
            "OTEL_SAMPLE_HTTP": "0.25",
            "OTEL_SAMPLE_ROUTES_REGEX": "(unclosed:1.0;^/ok.*:0.6",
        }
    )
    # Invalid regex should be ignored; valid pattern applies
    assert m.get_effective_http_sample("/ok/path") == 0.6
    # Non-matching path falls back to HTTP base
    assert m.get_effective_http_sample("/other") == 0.25
