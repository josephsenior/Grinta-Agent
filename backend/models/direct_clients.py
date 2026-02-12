"""Direct LLM clients for OpenAI, Anthropic, Google Gemini, and xAI Grok.

This module provides direct SDK integrations with major LLM providers,
offering a lightweight and stable alternative to multi-provider abstraction libraries.
"""

from __future__ import annotations

import os
import json
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Union, Protocol
from abc import ABC, abstractmethod

import httpx
from openai import OpenAI, AsyncOpenAI
from anthropic import Anthropic, AsyncAnthropic
import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse

from backend.core.logger import forge_logger as logger
from backend.core.exceptions import LLMNoResponseError

class LLMResponse:
    """Standardized response object for LLM calls with attribute and dict access."""
    def __init__(
        self,
        content: str,
        model: str,
        usage: Dict[str, int],
        id: str = "",
        finish_reason: str = "stop",
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        self.content = content
        self.model = model
        self.usage = usage
        self.id = kwargs.get("response_id", id)
        self.finish_reason = finish_reason
        self.tool_calls = tool_calls
        
        # Build nested structure for backwards compatibility (attribute access)
        class Message:
            def __init__(self, content, role, tool_calls=None):
                self.content = content
                self.role = role
                self.tool_calls = tool_calls
                
        class Choice:
            def __init__(self, content, role, finish_reason, tool_calls=None):
                self.message = Message(content, role, tool_calls)
                self.finish_reason = finish_reason

        self.choices = [Choice(content, "assistant", finish_reason, tool_calls)]

    def to_dict(self) -> Dict[str, Any]:
        message: Dict[str, Any] = {"content": self.content, "role": "assistant"}
        if self.tool_calls:
            message["tool_calls"] = self.tool_calls  # type: ignore[assignment]
            
        return {
            "choices": [
                {
                    "message": message,
                    "finish_reason": self.finish_reason
                }
            ],
            "usage": self.usage,
            "id": self.id,
            "model": self.model
        }

    def __getitem__(self, key):
        """Allow dict-like access to the underlying dict representation."""
        return self.to_dict()[key]

class DirectLLMClient(ABC):
    """Abstract base class for direct LLM clients."""
    
    @abstractmethod
    def completion(self, messages: List[Dict[str, Any]], **kwargs) -> LLMResponse:
        pass

    @abstractmethod
    async def acompletion(self, messages: List[Dict[str, Any]], **kwargs) -> LLMResponse:
        pass

    @abstractmethod
    async def astream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncIterator[Dict[str, Any]]:  # type: ignore[override,misc]
        """Stream responses asynchronously. Returns an async iterator."""
        pass

    def __init_subclass__(cls, **kwargs):
        """Ensure subclasses define model_name attribute."""
        super().__init_subclass__(**kwargs)
    
    @property
    def model_name(self) -> str:
        """Get the model name. Must be implemented by subclasses."""
        if not hasattr(self, '_model_name'):
            raise NotImplementedError("Subclasses must set _model_name attribute")
        return self._model_name
    
    def get_completion_cost(self, prompt_tokens: int, completion_tokens: int, config: Optional[Any] = None) -> float:
        """Calculate completion cost for this client's model."""
        from backend.models.cost_tracker import get_completion_cost
        return get_completion_cost(self.model_name, prompt_tokens, completion_tokens, config)

class OpenAIClient(DirectLLMClient):
    """Client for OpenAI and OpenAI-compatible APIs (like xAI Grok)."""
    
    def __init__(self, model_name: str, api_key: str, base_url: Optional[str] = None):
        self._model_name = model_name
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    @staticmethod
    def _extract_openai_tool_calls(message: Any) -> Optional[List[Dict[str, Any]]]:
        """Extract tool_calls from an OpenAI ChatCompletionMessage."""
        raw = getattr(message, "tool_calls", None)
        if not raw:
            return None
        result: List[Dict[str, Any]] = []
        for tc in raw:
            entry: Dict[str, Any] = {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            result.append(entry)
        return result or None

    def completion(self, messages: List[Dict[str, Any]], **kwargs) -> LLMResponse:
        if "model" not in kwargs:
            kwargs["model"] = self.model_name
        response = self.client.chat.completions.create(
            messages=messages,  # type: ignore[arg-type]
            **kwargs
        )
        msg = response.choices[0].message
        tool_calls = self._extract_openai_tool_calls(msg)
        return LLMResponse(
            content=msg.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            id=response.id,
            finish_reason=response.choices[0].finish_reason,
            tool_calls=tool_calls,
        )

    async def acompletion(self, messages: List[Dict[str, Any]], **kwargs) -> LLMResponse:
        if "model" not in kwargs:
            kwargs["model"] = self.model_name
        response = await self.async_client.chat.completions.create(
            messages=messages,  # type: ignore[arg-type]
            **kwargs
        )
        msg = response.choices[0].message
        tool_calls = self._extract_openai_tool_calls(msg)
        return LLMResponse(
            content=msg.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            id=response.id,
            finish_reason=response.choices[0].finish_reason,
            tool_calls=tool_calls,
        )

    async def astream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncIterator[Dict[str, Any]]:  # type: ignore[override,misc]
        kwargs["stream"] = True
        if "model" not in kwargs:
            kwargs["model"] = self.model_name
        stream = await self.async_client.chat.completions.create(
            messages=messages,  # type: ignore[arg-type]
            **kwargs
        )
        async for chunk in stream:  # type: ignore[attr-defined]
            yield chunk.model_dump()

class AnthropicClient(DirectLLMClient):
    """Client for Anthropic Claude."""
    
    def __init__(self, model_name: str, api_key: str):
        self._model_name = model_name
        self.client = Anthropic(api_key=api_key)
        self.async_client = AsyncAnthropic(api_key=api_key)

    @staticmethod
    def _extract_anthropic_tool_calls(content_blocks: list) -> tuple[str, Optional[List[Dict[str, Any]]]]:
        """Extract text and tool_use blocks from Anthropic response content.

        Returns:
            (text_content, tool_calls_or_None)
        """
        text_parts: list[str] = []
        tool_calls: List[Dict[str, Any]] = []
        for block in content_blocks:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                text_parts.append(block.text)
            elif block_type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "type": "function",
                    "function": {
                        "name": block.name,
                        "arguments": json.dumps(block.input) if isinstance(block.input, dict) else str(block.input),
                    },
                })
        return "\n".join(text_parts), tool_calls or None

    def _prepare_anthropic_kwargs(self, messages: List[Dict[str, Any]], kwargs: Dict[str, Any]) -> tuple[list, Dict[str, Any]]:
        """Extract system message and set model for Anthropic calls."""
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
        filtered = [m for m in messages if m["role"] != "system"]
        if "model" not in kwargs:
            kwargs["model"] = self.model_name
        if system_msg is not None:
            kwargs["system"] = system_msg
        return filtered, kwargs

    def completion(self, messages: List[Dict[str, Any]], **kwargs) -> LLMResponse:
        filtered, kwargs = self._prepare_anthropic_kwargs(messages, kwargs)
        response = self.client.messages.create(
            messages=filtered,  # type: ignore[arg-type]
            **kwargs
        )
        content, tool_calls = self._extract_anthropic_tool_calls(response.content)
        return LLMResponse(
            content=content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            id=response.id,
            finish_reason=response.stop_reason or "stop",
            tool_calls=tool_calls,
        )

    async def acompletion(self, messages: List[Dict[str, Any]], **kwargs) -> LLMResponse:
        filtered, kwargs = self._prepare_anthropic_kwargs(messages, kwargs)
        response = await self.async_client.messages.create(
            messages=filtered,  # type: ignore[arg-type]
            **kwargs
        )
        content, tool_calls = self._extract_anthropic_tool_calls(response.content)
        return LLMResponse(
            content=content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            id=response.id,
            finish_reason=response.stop_reason or "stop",
            tool_calls=tool_calls,
        )

    async def astream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncIterator[Dict[str, Any]]:  # type: ignore[override,misc]
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
        filtered_messages = [m for m in messages if m["role"] != "system"]
        
        if "model" not in kwargs:
            kwargs["model"] = self.model_name
            
        async with self.async_client.messages.stream(
            messages=filtered_messages,  # type: ignore[arg-type]
            system=system_msg,  # type: ignore[arg-type]
            **kwargs
        ) as stream:
            async for event in stream:
                # Convert Anthropic events to OpenAI-like chunks for compatibility
                if event.type == "content_block_delta":
                    yield {
                        "choices": [
                            {
                                "delta": {"content": event.delta.text},  # type: ignore[union-attr]
                                "finish_reason": None
                            }
                        ]
                    }
                elif event.type == "message_stop":
                    yield {
                        "choices": [
                            {
                                "delta": {},
                                "finish_reason": "stop"
                            }
                        ]
                    }

class GeminiClient(DirectLLMClient):
    """Client for Google Gemini."""
    
    def __init__(self, model_name: str, api_key: str):
        self._model_name = model_name
        genai.configure(api_key=api_key)
        self.api_key = api_key

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """Convert messages to Gemini format, extracting system instruction.

        Returns:
            (system_instruction_or_None, gemini_history_messages)
        """
        system_instruction: Optional[str] = None
        gemini_messages: List[Dict[str, Any]] = []
        for m in messages:
            if m["role"] == "system":
                system_instruction = m["content"]
                continue
            role = "user" if m["role"] == "user" else "model"
            gemini_messages.append({"role": role, "parts": [m["content"]]})
        return system_instruction, gemini_messages

    @staticmethod
    def _extract_gemini_generation_config(kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Pop generation-config keys from *kwargs* and return (model_name, gen_config)."""
        model_name = kwargs.pop("model", "")
        if "/" in model_name:
            model_name = model_name.split("/")[-1]
        gen_cfg: Dict[str, Any] = {}
        for src, dst in [
            ("temperature", "temperature"),
            ("top_p", "top_p"),
            ("top_k", "top_k"),
            ("max_tokens", "max_output_tokens"),
            ("stop", "stop_sequences"),
        ]:
            if src in kwargs:
                gen_cfg[dst] = kwargs.pop(src)
        return model_name, gen_cfg

    @staticmethod
    def _extract_gemini_tool_calls(response: Any) -> Optional[List[Dict[str, Any]]]:
        """Extract function call parts from a Gemini response."""
        tool_calls: List[Dict[str, Any]] = []
        for candidate in getattr(response, "candidates", []):
            for part in getattr(candidate, "content", {}).get("parts", []):
                fc = getattr(part, "function_call", None)
                if fc is None:
                    continue
                tool_calls.append({
                    "id": f"gemini-{len(tool_calls)}",
                    "type": "function",
                    "function": {
                        "name": fc.name,
                        "arguments": json.dumps(dict(fc.args)) if fc.args else "{}",
                    },
                })
        return tool_calls or None

    @staticmethod
    def _gemini_usage(response: Any) -> Dict[str, int]:
        """Extract token usage from a Gemini response."""
        meta = getattr(response, "usage_metadata", None)
        return {
            "prompt_tokens": getattr(meta, "prompt_token_count", 0) if meta else 0,
            "completion_tokens": getattr(meta, "candidates_token_count", 0) if meta else 0,
            "total_tokens": getattr(meta, "total_token_count", 0) if meta else 0,
        }

    def _build_gemini_chat(self, messages: List[Dict[str, Any]], kwargs: Dict[str, Any]):
        """Shared setup for Gemini completion / acompletion / astream."""
        model_name, gen_cfg = self._extract_gemini_generation_config(kwargs)
        model_name = model_name or self.model_name
        if "/" in model_name:
            model_name = model_name.split("/")[-1]
        system_instruction, gemini_messages = self._convert_messages(messages)
        model_kwargs: Dict[str, Any] = {"generation_config": gen_cfg} if gen_cfg else {}
        if system_instruction:
            model_kwargs["system_instruction"] = system_instruction
        model = genai.GenerativeModel(model_name, **model_kwargs)  # type: ignore[arg-type]
        prompt = gemini_messages[-1]["parts"][0] if gemini_messages else ""
        history = gemini_messages[:-1] if gemini_messages else []
        chat = model.start_chat(history=history)  # type: ignore[arg-type]
        return model_name, chat, prompt

    def completion(self, messages: List[Dict[str, Any]], **kwargs) -> LLMResponse:
        model_name, chat, prompt = self._build_gemini_chat(messages, kwargs)
        response = chat.send_message(prompt, **kwargs)
        return LLMResponse(
            content=response.text,
            model=model_name,
            usage=self._gemini_usage(response),
            id="",
            finish_reason="stop",
            tool_calls=self._extract_gemini_tool_calls(response),
        )

    async def acompletion(self, messages: List[Dict[str, Any]], **kwargs) -> LLMResponse:
        model_name, chat, prompt = self._build_gemini_chat(messages, kwargs)
        response = await chat.send_message_async(prompt, **kwargs)
        return LLMResponse(
            content=response.text,
            model=model_name,
            usage=self._gemini_usage(response),
            id="",
            finish_reason="stop",
            tool_calls=self._extract_gemini_tool_calls(response),
        )

    async def astream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncIterator[Dict[str, Any]]:  # type: ignore[override,misc]
        model_name, chat, prompt = self._build_gemini_chat(messages, kwargs)
        response = await chat.send_message_async(prompt, stream=True, **kwargs)
        
        async for chunk in response:
            yield {
                "choices": [
                    {
                        "delta": {"content": chunk.text},
                        "finish_reason": None
                    }
                ]
            }
        yield {
            "choices": [
                {
                    "delta": {},
                    "finish_reason": "stop"
                }
            ]
        }

def get_direct_client(model: str, api_key: str, base_url: Optional[str] = None) -> DirectLLMClient:
    """Factory function to get the correct direct client."""
    model_lower = model.lower()
    
    if "anthropic" in model_lower or "claude" in model_lower:
        return AnthropicClient(model_name=model, api_key=api_key)
    elif "google" in model_lower or "gemini" in model_lower:
        return GeminiClient(model_name=model, api_key=api_key)
    elif "xai" in model_lower or "grok" in model_lower:
        return OpenAIClient(model_name=model, api_key=api_key, base_url="https://api.x.ai/v1")
    else:
        # Default to OpenAI
        return OpenAIClient(model_name=model, api_key=api_key, base_url=base_url)
