"""Backwards-compatibility shim – canonical location is forge.core.type_safety."""

from backend.core.type_safety import (  # noqa: F401
    MISSING,
    NOT_SET,
    Sentinel,
    is_missing,
    is_not_set,
    is_set,
    PathValidator,
    SafePath,
    validate_and_sanitize_path,
    NonEmptyString,
    PositiveInt,
    SafeDict,
    SafeList,
    validate_non_empty_string,
    validate_positive_int,
)

__all__ = [
    # Sentinels
    "MISSING",
    "NOT_SET",
    "Sentinel",
    "is_missing",
    "is_not_set",
    "is_set",
    # Path validation
    "PathValidator",
    "SafePath",
    "validate_and_sanitize_path",
    # Type safety
    "NonEmptyString",
    "PositiveInt",
    "SafeDict",
    "SafeList",
    "validate_non_empty_string",
    "validate_positive_int",
]

