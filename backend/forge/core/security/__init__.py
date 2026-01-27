"""Security and robustness utilities for Forge.

Provides:
- Sentinel objects for explicit None handling
- Type-safe wrappers
- Security boundaries
- Defensive programming utilities
"""

from forge.core.security.sentinels import (
    MISSING,
    NOT_SET,
    Sentinel,
    is_missing,
    is_not_set,
    is_set,
)
from forge.core.security.path_validation import (
    PathValidator,
    SafePath,
    validate_and_sanitize_path,
)
from forge.core.security.type_safety import (
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

