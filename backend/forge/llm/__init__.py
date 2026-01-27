"""Llm module public API."""

from forge.llm.llm import LLM

# Aliases for backwards compatibility
AsyncLLM = LLM
StreamingLLM = LLM

__all__ = ["LLM", "AsyncLLM", "StreamingLLM"]
