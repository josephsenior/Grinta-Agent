"""Llm module public API."""

from backend.models.llm import LLM

# Aliases for backwards compatibility
AsyncLLM = LLM
StreamingLLM = LLM

__all__ = ["LLM", "AsyncLLM", "StreamingLLM"]
