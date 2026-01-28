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

from forge.core.logger import forge_logger as logger
from forge.core.exceptions import LLMNoResponseError

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
        from forge.llm.cost_tracker import get_completion_cost
        return get_completion_cost(self.model_name, prompt_tokens, completion_tokens, config)

class OpenAIClient(DirectLLMClient):
    """Client for OpenAI and OpenAI-compatible APIs (like xAI Grok)."""
    
    def __init__(self, model_name: str, api_key: str, base_url: Optional[str] = None):
        self._model_name = model_name
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    def completion(self, messages: List[Dict[str, Any]], **kwargs) -> LLMResponse:
        if "model" not in kwargs:
            kwargs["model"] = self.model_name
        response = self.client.chat.completions.create(
            messages=messages,  # type: ignore[arg-type]
            **kwargs
        )
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            id=response.id,
            finish_reason=response.choices[0].finish_reason
        )

    async def acompletion(self, messages: List[Dict[str, Any]], **kwargs) -> LLMResponse:
        if "model" not in kwargs:
            kwargs["model"] = self.model_name
        response = await self.async_client.chat.completions.create(
            messages=messages,  # type: ignore[arg-type]
            **kwargs
        )
        return LLMResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            },
            id=response.id,
            finish_reason=response.choices[0].finish_reason
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

    def completion(self, messages: List[Dict[str, Any]], **kwargs) -> LLMResponse:
        # Anthropic doesn't support 'system' role in messages list, but as a top-level param
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
        filtered_messages = [m for m in messages if m["role"] != "system"]
        
        if "model" not in kwargs:
            kwargs["model"] = self.model_name
            
        response = self.client.messages.create(
            messages=filtered_messages,  # type: ignore[arg-type]
            system=system_msg,  # type: ignore[arg-type]
            **kwargs
        )
        return LLMResponse(
            content=response.content[0].text,  # type: ignore[union-attr]
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            id=response.id,
            finish_reason=response.stop_reason or "stop"
        )

    async def acompletion(self, messages: List[Dict[str, Any]], **kwargs) -> LLMResponse:
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
        filtered_messages = [m for m in messages if m["role"] != "system"]
        
        if "model" not in kwargs:
            kwargs["model"] = self.model_name
            
        response = await self.async_client.messages.create(
            messages=filtered_messages,  # type: ignore[arg-type]
            system=system_msg,  # type: ignore[arg-type]
            **kwargs
        )
        return LLMResponse(
            content=response.content[0].text,  # type: ignore[union-attr]
            model=response.model,
            usage={
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            },
            id=response.id,
            finish_reason=response.stop_reason or "stop"
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

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Gemini uses 'user' and 'model' roles
        gemini_messages = []
        for m in messages:
            role = "user" if m["role"] in ["user", "system"] else "model"
            gemini_messages.append({"role": role, "parts": [m["content"]]})
        return gemini_messages

    def completion(self, messages: List[Dict[str, Any]], **kwargs) -> LLMResponse:
        model_name = kwargs.pop("model", self.model_name)
        # Handle model names that might have prefixes
        if "/" in model_name:
            model_name = model_name.split("/")[-1]
            
        # Extract generation config from kwargs
        generation_config = {}
        if "temperature" in kwargs:
            generation_config["temperature"] = kwargs.pop("temperature")
        if "top_p" in kwargs:
            generation_config["top_p"] = kwargs.pop("top_p")
        if "top_k" in kwargs:
            generation_config["top_k"] = kwargs.pop("top_k")
        if "max_tokens" in kwargs:
            generation_config["max_output_tokens"] = kwargs.pop("max_tokens")
        if "stop" in kwargs:
            generation_config["stop_sequences"] = kwargs.pop("stop")
            
        model = genai.GenerativeModel(model_name, generation_config=generation_config)  # type: ignore[arg-type]
        gemini_messages = self._convert_messages(messages)
        
        # Last message is the prompt
        prompt = gemini_messages[-1]["parts"][0]
        history = gemini_messages[:-1]
        
        chat = model.start_chat(history=history)  # type: ignore[arg-type]
        response = chat.send_message(prompt, **kwargs)
        
        return LLMResponse(
            content=response.text,
            model=model_name,
            usage={
                "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, "usage_metadata") else 0,
                "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, "usage_metadata") else 0,
                "total_tokens": response.usage_metadata.total_token_count if hasattr(response, "usage_metadata") else 0,
            },
            id="",
            finish_reason="stop"
        )

    async def acompletion(self, messages: List[Dict[str, Any]], **kwargs) -> LLMResponse:
        model_name = kwargs.pop("model", self.model_name)
        if "/" in model_name:
            model_name = model_name.split("/")[-1]

        # Extract generation config from kwargs
        generation_config = {}
        if "temperature" in kwargs:
            generation_config["temperature"] = kwargs.pop("temperature")
        if "top_p" in kwargs:
            generation_config["top_p"] = kwargs.pop("top_p")
        if "top_k" in kwargs:
            generation_config["top_k"] = kwargs.pop("top_k")
        if "max_tokens" in kwargs:
            generation_config["max_output_tokens"] = kwargs.pop("max_tokens")
        if "stop" in kwargs:
            generation_config["stop_sequences"] = kwargs.pop("stop")

        model = genai.GenerativeModel(model_name, generation_config=generation_config)  # type: ignore[arg-type]
        gemini_messages = self._convert_messages(messages)
        
        prompt = gemini_messages[-1]["parts"][0]
        history = gemini_messages[:-1]
        
        chat = model.start_chat(history=history)  # type: ignore[arg-type]
        response = await chat.send_message_async(prompt, **kwargs)
        
        return LLMResponse(
            content=response.text,
            model=model_name,
            usage={
                "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, "usage_metadata") else 0,
                "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, "usage_metadata") else 0,
                "total_tokens": response.usage_metadata.total_token_count if hasattr(response, "usage_metadata") else 0,
            },
            id="",
            finish_reason="stop"
        )

    async def astream(self, messages: List[Dict[str, Any]], **kwargs) -> AsyncIterator[Dict[str, Any]]:  # type: ignore[override,misc]
        model_name = kwargs.pop("model", self.model_name)
        if "/" in model_name:
            model_name = model_name.split("/")[-1]

        # Extract generation config from kwargs
        generation_config = {}
        if "temperature" in kwargs:
            generation_config["temperature"] = kwargs.pop("temperature")
        if "top_p" in kwargs:
            generation_config["top_p"] = kwargs.pop("top_p")
        if "top_k" in kwargs:
            generation_config["top_k"] = kwargs.pop("top_k")
        if "max_tokens" in kwargs:
            generation_config["max_output_tokens"] = kwargs.pop("max_tokens")
        if "stop" in kwargs:
            generation_config["stop_sequences"] = kwargs.pop("stop")

        model = genai.GenerativeModel(model_name, generation_config=generation_config)  # type: ignore[arg-type]
        gemini_messages = self._convert_messages(messages)
        
        prompt = gemini_messages[-1]["parts"][0]
        history = gemini_messages[:-1]
        
        chat = model.start_chat(history=history)  # type: ignore[arg-type]
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
