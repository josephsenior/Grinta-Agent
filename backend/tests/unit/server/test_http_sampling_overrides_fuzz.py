import importlib
import os
import sys
from typing import List

from hypothesis import given, strategies as st, settings, HealthCheck

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Restrict route characters to a conservative safe set to avoid generating
# delimiter characters (semicolon, colon, asterisk) that would break the
# simple env-string parser used in production. This keeps the fuzzing focused
# on realistic HTTP paths while still exploring edge cases.
SAFE_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
ROUTE_SEGMENT = st.text(st.sampled_from(list(SAFE_CHARS)), min_size=1, max_size=12)
ROUTE_PATH = st.lists(ROUTE_SEGMENT, min_size=1, max_size=5).map(
    lambda segs: "/" + "/".join(segs)
)

FLOAT_RATE = st.floats(
    min_value=-2.0, max_value=2.0, allow_infinity=False, allow_nan=False
)

SIMPLE_ENTRY = st.tuples(ROUTE_PATH, FLOAT_RATE).map(lambda t: f"{t[0]}:{t[1]:.3f}")
PREFIX_ENTRY = st.tuples(ROUTE_PATH, FLOAT_RATE).map(lambda t: f"{t[0]}*:{t[1]:.3f}")
REGEX_SAFE = st.from_regex(r"^[A-Za-z0-9_/.*^$()+?|\\-]+$", fullmatch=True)
REGEX_ENTRY = st.tuples(REGEX_SAFE, FLOAT_RATE).map(lambda t: f"{t[0]}:{t[1]:.3f}")

COMBINED_SIMPLE = st.lists(
    st.one_of(SIMPLE_ENTRY, PREFIX_ENTRY), min_size=0, max_size=8
).map(lambda lst: ";".join(lst))
COMBINED_REGEX = st.lists(REGEX_ENTRY, min_size=0, max_size=5).map(
    lambda lst: ";".join(lst)
)

TEST_ROUTE = ROUTE_PATH


def reload_app(
    simple_overrides: str,
    regex_overrides: str,
    sample_http: float,
    sample_default: float,
):
    # Clean env
    for k in list(os.environ.keys()):
        if (
            k.startswith("OTEL_SAMPLE_HTTP")
            or k.startswith("OTEL_SAMPLE_ROUTES")
            or k.startswith("OTEL_SAMPLE_DEFAULT")
            or k.startswith("OTEL_SAMPLE_ROUTES_REGEX")
        ):
            os.environ.pop(k, None)
    os.environ["OTEL_ENABLED"] = "true"
    os.environ["OTEL_SAMPLE_HTTP"] = f"{sample_http}"
    os.environ["OTEL_SAMPLE_DEFAULT"] = f"{sample_default}"
    if simple_overrides:
        os.environ["OTEL_SAMPLE_ROUTES"] = simple_overrides
    if regex_overrides:
        os.environ["OTEL_SAMPLE_ROUTES_REGEX"] = regex_overrides
    if "forge.server.app" in sys.modules:
        del sys.modules["forge.server.app"]
    return importlib.import_module("forge.server.app")


@settings(deadline=None, suppress_health_check=[HealthCheck.too_slow], max_examples=50)
@given(
    simple_overrides=COMBINED_SIMPLE,
    regex_overrides=COMBINED_REGEX,
    sample_http=FLOAT_RATE,
    sample_default=FLOAT_RATE,
    route=TEST_ROUTE,
)
def test_effective_rate_bounds(
    simple_overrides, regex_overrides, sample_http, sample_default, route
):
    module = reload_app(simple_overrides, regex_overrides, sample_http, sample_default)
    rate = module.get_effective_http_sample(route)
    # All returned rates must be clamped to [0.0, 1.0]
    assert 0.0 <= rate <= 1.0


@settings(deadline=None, max_examples=80)
@given(
    sample_http=FLOAT_RATE,
    sample_default=FLOAT_RATE,
    route=TEST_ROUTE,
)
def test_fallback_when_no_overrides(sample_http, sample_default, route):
    module = reload_app("", "", sample_http, sample_default)
    expected = sample_http if "OTEL_SAMPLE_HTTP" in os.environ else sample_default
    # Our implementation always sets OTEL_SAMPLE_HTTP explicitly, so fallback is sample_http
    rate = module.get_effective_http_sample(route)
    assert rate == module._sample_http  # internal consistency
    assert 0.0 <= rate <= 1.0


@settings(deadline=None, max_examples=80)
@given(
    prefix=ROUTE_PATH,
    sample_http=FLOAT_RATE,
    sample_default=FLOAT_RATE,
    route=ROUTE_PATH,
)
def test_prefix_match_applies(prefix, sample_http, sample_default, route):
    simple = f"{prefix}*:1.0"
    module = reload_app(simple, "", sample_http, sample_default)
    # If route starts with prefix, must be 1.0 else fallback
    rate = module.get_effective_http_sample(route)
    if route.startswith(prefix):
        assert rate == 1.0
    else:
        assert rate == module._sample_http


@settings(deadline=None, max_examples=80)
@given(
    regex=REGEX_ENTRY,
    sample_http=FLOAT_RATE,
    sample_default=FLOAT_RATE,
    route=ROUTE_PATH,
)
def test_regex_precedence(regex, sample_http, sample_default, route):
    regex_pattern, rate_str = regex.split(":", 1)
    module = reload_app("", regex, sample_http, sample_default)
    eff = module.get_effective_http_sample(route)
    # If regex matches, rate applied (clamped). If not, fallback to HTTP base.
    import re as _re

    try:
        cre = _re.compile(regex_pattern)
    except Exception:
        # invalid regex is ignored; fallback
        assert eff == module._sample_http
        return
    if cre.search(route):
        # Rate string converted to float then clamped in parsing
        parsed_rate = float(rate_str)
        parsed_rate = max(0.0, min(1.0, parsed_rate))
        assert eff == parsed_rate
    else:
        assert eff == module._sample_http
