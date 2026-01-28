"""Common exception types for LLM operations.

These are used to provide a consistent error interface regardless of the
underlying provider SDK.
"""

from typing import Optional

class LLMError(Exception):
    """Base exception for all LLM-related errors."""
    def __init__(
        self,
        message: str,
        llm_provider: Optional[str] = None,
        model: Optional[str] = None,
        status_code: Optional[int] = None,
        *args,
        **kwargs
    ):
        super().__init__(message, *args)
        self.message = message
        self.llm_provider = llm_provider
        self.model = model
        self.status_code = status_code
        self.kwargs = kwargs

class APIConnectionError(LLMError):
    """Error connecting to the LLM API."""
    pass

class APIError(LLMError):
    """Generic API error from the LLM provider."""
    pass

class AuthenticationError(LLMError):
    """Authentication or API key error."""
    pass

class BadRequestError(LLMError):
    """Invalid request parameters or format."""
    pass

class ContentPolicyViolationError(LLMError):
    """Content blocked by safety filters or policy."""
    pass

class ContextWindowExceededError(LLMError):
    """Input or output exceeded the model's context window."""
    pass

class InternalServerError(LLMError):
    """Server-side error from the LLM provider."""
    pass

class NotFoundError(LLMError):
    """Requested model or resource not found."""
    pass

class RateLimitError(LLMError):
    """API rate limit exceeded."""
    pass

class ServiceUnavailableError(LLMError):
    """LLM service is temporarily unavailable."""
    pass

class Timeout(LLMError):
    """Request timed out."""
    pass

class OpenAIError(LLMError):
    """OpenAI-specific error."""
    pass
