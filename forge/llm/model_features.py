"""Model capability detection helpers used to gate Forge LLM features."""

from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch


def normalize_model_name(model: str) -> str:
    """Normalize a model string to a canonical, comparable name.

    Strategy:
    - Trim whitespace
    - Lowercase
    - If there is a '/', keep only the basename after the last '/'
      (handles prefixes like openrouter/, litellm_proxy/, anthropic/, etc.)
      and treat ':' inside that basename as an Ollama-style variant tag to be removed
    - There is no provider:model form; providers, when present, use 'provider/model'
    - Drop a trailing "-gguf" suffix if present
    """
    raw = (model or "").strip().lower()
    if "/" in raw:
        name = raw.split("/")[-1]
        if ":" in name:
            name = name.split(":", 1)[0]
    else:
        name = raw
    return name.removesuffix("-gguf")


def model_matches(model: str, patterns: list[str]) -> bool:
    """Return True if the model matches any of the glob patterns.

    If a pattern contains a '/', it is treated as provider-qualified and matched
    against the full, lowercased model string (including provider prefix).
    Otherwise, it is matched against the normalized basename.
    """
    raw = (model or "").strip().lower()
    name = normalize_model_name(model)
    for pat in patterns:
        pat_l = pat.lower()
        if ("/" in pat_l and fnmatch(raw, pat_l)) or (
            "/" not in pat_l and fnmatch(name, pat_l)
        ):
            return True
    return False


@dataclass(frozen=True)
class ModelFeatures:
    """Capabilities and limits reported for a particular LLM provider/model pair."""

    max_tokens: int | None = None
    supports_function_calling: bool = False
    supports_reasoning_effort: bool = False
    supports_prompt_cache: bool = False
    supports_stop_words: bool = True


FUNCTION_CALLING_PATTERNS: list[str] = [
    "claude-3-7-sonnet*",
    "claude-3.7-sonnet*",
    "claude-sonnet-3-7-latest",
    "claude-3-5-sonnet*",
    "claude-3.5-haiku*",
    "claude-3-5-haiku*",
    "claude-sonnet-4*",
    "claude-opus-4*",
    "claude-4.5-*",  # Claude 4.5 series (all variants)
    "claude-4-5-*",  # Claude 4.5 series (hyphen format)
    "claude-sonnet-4.5*",  # Claude Sonnet 4.5
    "claude-haiku-4.5*",  # Claude Haiku 4.5
    "claude-sonnet-4-5-*",  # Claude Sonnet 4.5 (dated format)
    "claude-haiku-4-5-*",  # Claude Haiku 4.5 (dated format)
    "gpt-4o*",
    "gpt-4.1",
    "gpt-5*",
    "o1-2024-12-17",
    "o3*",
    "o4-mini*",
    "gemini/gemini-1.5-*",  # All Gemini 1.5 models (flash, pro, etc)
    "gemini/gemini-2.0-*",  # All Gemini 2.0 models (flash-exp, pro, etc)
    "gemini/gemini-2.5-*",  # All Gemini 2.5 models (flash, pro, etc)
    "gemini-2.5-pro*",
    "gemini-2.5-flash*",
    "kimi-k2-0711-preview",
    "kimi-k2-instruct",
    "qwen3-coder*",
    "qwen3-coder-480b-a35b-instruct",
    "deepseek-chat",
]
REASONING_EFFORT_PATTERNS: list[str] = [
    "o1-2024-12-17",
    "o1",
    "o3",
    "o3-2025-04-16",
    "o3-mini-2025-01-31",
    "o3-mini",
    "o4-mini",
    "o4-mini-2025-04-16",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gpt-5*",
    "deepseek-r1-0528*",
]
PROMPT_CACHE_PATTERNS: list[str] = [
    "claude-3-7-sonnet*",
    "claude-3.7-sonnet*",
    "claude-sonnet-3-7-latest",
    "claude-3-5-sonnet*",
    "claude-3-5-haiku*",
    "claude-3.5-haiku*",
    "claude-3-haiku-20240307",
    "claude-3-opus-20240229",
    "claude-sonnet-4*",
    "claude-opus-4*",
]
SUPPORTS_STOP_WORDS_FALSE_PATTERNS: list[str] = [
    "o1*",
    "grok-4-0709",
    "grok-4*",
    "grok-code-fast-1*",
    "deepseek-r1-0528*",
]


def get_features(model: str) -> ModelFeatures:
    """Get feature capabilities for a specific model.

    Args:
        model: Model identifier

    Returns:
        ModelFeatures object with capability flags

    """
    return ModelFeatures(
        supports_function_calling=model_matches(model, FUNCTION_CALLING_PATTERNS),
        supports_reasoning_effort=model_matches(model, REASONING_EFFORT_PATTERNS),
        supports_prompt_cache=model_matches(model, PROMPT_CACHE_PATTERNS),
        supports_stop_words=not model_matches(
            model, SUPPORTS_STOP_WORDS_FALSE_PATTERNS
        ),
    )
