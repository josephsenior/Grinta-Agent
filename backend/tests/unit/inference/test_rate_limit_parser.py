from backend.inference.exceptions import RateLimitKind
from backend.inference.rate_limit_parser import classify_rate_limit


def test_codex_subscription_usage_limit_is_classified_as_capacity() -> None:
    error = RuntimeError(
        '{"type":"usage_limit_reached","message":"Usage limit has been reached",'
        '"plan_type":"plus","resets_in_seconds":7200}'
    )

    kind, _ = classify_rate_limit(error)

    assert kind is RateLimitKind.USAGE_QUOTA
