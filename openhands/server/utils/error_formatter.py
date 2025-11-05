"""
User-Friendly Error Formatting System

This module provides production-grade error formatting that converts technical
errors into user-friendly messages with actionable suggestions.

Features:
- Plain English error messages
- Actionable suggestions
- Visual icons and formatting
- Retry/recovery actions
- Help documentation links
- Technical details (collapsible)
- Error analytics tracking
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from openhands.core.exceptions import (
    AgentStuckInLoopError,
    FunctionCallNotExistsError,
    FunctionCallValidationError,
    LLMContextWindowExceedError,
    LLMMalformedActionError,
    LLMNoActionError,
    LLMNoResponseError,
    LLMResponseError,
    UserCancelledError,
    AgentRuntimeUnavailableError,
)
from openhands.core.logger import openhands_logger as logger


class ErrorSeverity(str, Enum):
    """Error severity levels for UX presentation."""
    INFO = "info"           # ℹ️ Informational (blue)
    WARNING = "warning"     # ⚠️ Warning (yellow)
    ERROR = "error"         # ❌ Error (red)
    CRITICAL = "critical"   # 🚨 Critical (red + urgent)


class ErrorCategory(str, Enum):
    """Error categories for better UX grouping."""
    USER_INPUT = "user_input"         # User made a mistake
    SYSTEM = "system"                 # System/infrastructure issue
    RATE_LIMIT = "rate_limit"         # Rate limiting/quota
    AUTHENTICATION = "authentication" # Auth/permissions
    NETWORK = "network"               # Network/connectivity
    AI_MODEL = "ai_model"             # LLM/AI model issue
    CONFIGURATION = "configuration"   # Config/setup issue


class ErrorAction:
    """Represents an action the user can take to resolve an error."""
    
    def __init__(
        self,
        label: str,
        action_type: str,
        url: Optional[str] = None,
        highlight: bool = False,
        data: Optional[dict[str, Any]] = None
    ):
        self.label = label
        self.action_type = action_type  # "retry", "new_session", "help", "upgrade", etc.
        self.url = url
        self.highlight = highlight  # Primary action
        self.data = data or {}
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "type": self.action_type,
            "url": self.url,
            "highlight": self.highlight,
            "data": self.data
        }


class UserFriendlyError:
    """User-friendly error with all presentation information."""
    
    def __init__(
        self,
        title: str,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        icon: str = "❌",
        suggestion: Optional[str] = None,
        actions: Optional[list[ErrorAction]] = None,
        technical_details: Optional[str] = None,
        error_code: Optional[str] = None,
        can_retry: bool = False,
        retry_delay: Optional[int] = None,
        help_url: Optional[str] = None,
        reassurance: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None
    ):
        self.title = title
        self.message = message
        self.severity = severity
        self.category = category
        self.icon = icon
        self.suggestion = suggestion
        self.actions = actions or []
        self.technical_details = technical_details
        self.error_code = error_code
        self.can_retry = can_retry
        self.retry_delay = retry_delay
        self.help_url = help_url
        self.reassurance = reassurance
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict for API response."""
        return {
            "title": self.title,
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "icon": self.icon,
            "suggestion": self.suggestion,
            "actions": [action.to_dict() for action in self.actions],
            "technical_details": self.technical_details,
            "error_code": self.error_code,
            "can_retry": self.can_retry,
            "retry_delay": self.retry_delay,
            "help_url": self.help_url,
            "reassurance": self.reassurance,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


def format_llm_no_response_error(error: LLMNoResponseError) -> UserFriendlyError:
    """Format LLM no response error for users."""
    return UserFriendlyError(
        title="AI didn't respond",
        message=(
            "The AI model timed out or returned an empty response.\n\n"
            "This sometimes happens when:\n"
            "• Your request is very complex\n"
            "• The AI service is experiencing high load\n"
            "• Your message triggered a content filter\n\n"
            "**Quick fix:** Try rephrasing your message or wait a minute."
        ),
        severity=ErrorSeverity.WARNING,
        category=ErrorCategory.AI_MODEL,
        icon="⏱️",
        suggestion="Rephrase your message and try again",
        actions=[
            ErrorAction("Try Again", "retry", highlight=True),
            ErrorAction("Simplify Request", "simplify"),
            ErrorAction("Get Help", "help", url="https://docs.forge.ai/errors/ai-timeout")
        ],
        technical_details=str(error),
        error_code="LLM_NO_RESPONSE",
        can_retry=True,
        retry_delay=60,
        help_url="https://docs.forge.ai/errors/ai-timeout"
    )


def format_context_window_error(error: LLMContextWindowExceedError) -> UserFriendlyError:
    """Format context window exceeded error for users."""
    return UserFriendlyError(
        title="Conversation too long",
        message=(
            "Your conversation has too much history for the AI to process.\n\n"
            "The AI can only remember a certain amount (think of it like short-term memory).\n\n"
            "**What to do:**\n"
            "• Start a new conversation (recommended)\n"
            "• Ask me to summarize what we've done\n"
            "• Export your work and continue fresh"
        ),
        severity=ErrorSeverity.WARNING,
        category=ErrorCategory.AI_MODEL,
        icon="💬",
        suggestion="Start a new conversation",
        actions=[
            ErrorAction("New Conversation", "new_conversation", highlight=True),
            ErrorAction("Summarize & Continue", "summarize"),
            ErrorAction("Export Work", "export")
        ],
        technical_details=str(error),
        error_code="CONTEXT_WINDOW_EXCEEDED",
        can_retry=False,
        help_url="https://docs.forge.ai/faq/context-limit",
        reassurance="Don't worry - all your work is saved!"
    )


def format_agent_stuck_error(error: AgentStuckInLoopError) -> UserFriendlyError:
    """Format agent stuck in loop error for users."""
    return UserFriendlyError(
        title="Agent stuck repeating actions",
        message=(
            "The AI is repeating the same action without making progress.\n\n"
            "This usually happens when:\n"
            "• The task is too vague or complex\n"
            "• There's missing information\n"
            "• The agent needs different permissions\n\n"
            "**How to fix:**\n"
            "• Break your task into smaller, specific steps\n"
            "• Provide more details about what you want\n"
            "• Try a different approach"
        ),
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.AI_MODEL,
        icon="🔄",
        suggestion="Break task into smaller steps",
        actions=[
            ErrorAction("Start Over", "new_conversation", highlight=True),
            ErrorAction("Get Examples", "help", url="https://docs.forge.ai/examples"),
        ],
        technical_details=str(error),
        error_code="AGENT_STUCK_IN_LOOP",
        can_retry=True,
        help_url="https://docs.forge.ai/troubleshooting/stuck-agent"
    )


def format_runtime_unavailable_error(error: AgentRuntimeUnavailableError) -> UserFriendlyError:
    """Format runtime unavailable error for users."""
    return UserFriendlyError(
        title="Workspace not ready",
        message=(
            "Your development environment isn't ready yet.\n\n"
            "This can happen when:\n"
            "• The system is still starting up (usually takes 30-60 seconds)\n"
            "• The container restarted due to an update\n"
            "• There was a temporary system issue\n\n"
            "**What to do:**\n"
            "• Wait 30 seconds and try again\n"
            "• Refresh the page\n"
            "• Start a new session if problem persists"
        ),
        severity=ErrorSeverity.WARNING,
        category=ErrorCategory.SYSTEM,
        icon="⏳",
        suggestion="Wait 30 seconds and retry",
        actions=[
            ErrorAction("Retry", "retry", highlight=True),
            ErrorAction("New Session", "new_conversation"),
        ],
        technical_details=str(error),
        error_code="RUNTIME_UNAVAILABLE",
        can_retry=True,
        retry_delay=30,
        help_url="https://docs.forge.ai/troubleshooting/runtime-issues",
        reassurance="Your work is safe! Just give it a moment."
    )


def format_function_call_error(error: FunctionCallValidationError | FunctionCallNotExistsError) -> UserFriendlyError:
    """Format function call errors for users."""
    return UserFriendlyError(
        title="AI tried to use an unavailable tool",
        message=(
            "The AI attempted to use a feature that's not available right now.\n\n"
            "This is usually temporary and can be fixed by:\n"
            "• Rephrasing your request differently\n"
            "• Trying a simpler approach first\n"
            "• Waiting a moment and trying again\n\n"
            "**Note:** This is a known issue we're working on!"
        ),
        severity=ErrorSeverity.WARNING,
        category=ErrorCategory.AI_MODEL,
        icon="🔧",
        suggestion="Rephrase your request",
        actions=[
            ErrorAction("Try Again", "retry", highlight=True),
            ErrorAction("Report Issue", "report", url="https://github.com/your-repo/issues"),
        ],
        technical_details=str(error),
        error_code="FUNCTION_CALL_ERROR",
        can_retry=True,
        help_url="https://docs.forge.ai/troubleshooting/tool-errors"
    )


def format_malformed_action_error(error: LLMMalformedActionError) -> UserFriendlyError:
    """Format malformed action error for users."""
    return UserFriendlyError(
        title="AI gave an unclear response",
        message=(
            "The AI's response wasn't formatted correctly.\n\n"
            "This is a temporary glitch that happens occasionally. Try:\n"
            "• Sending your message again\n"
            "• Simplifying your request\n"
            "• Breaking it into smaller tasks\n\n"
            "If this keeps happening, please let us know!"
        ),
        severity=ErrorSeverity.WARNING,
        category=ErrorCategory.AI_MODEL,
        icon="🤖",
        suggestion="Try sending your message again",
        actions=[
            ErrorAction("Retry", "retry", highlight=True),
            ErrorAction("Report Bug", "report", url="https://github.com/your-repo/issues"),
        ],
        technical_details=str(error),
        error_code="MALFORMED_ACTION",
        can_retry=True,
        help_url="https://docs.forge.ai/troubleshooting/ai-errors"
    )


def format_user_cancelled_error(error: UserCancelledError) -> UserFriendlyError:
    """Format user cancelled error."""
    return UserFriendlyError(
        title="Action cancelled",
        message="You cancelled this action. No changes were made.",
        severity=ErrorSeverity.INFO,
        category=ErrorCategory.USER_INPUT,
        icon="ℹ️",
        suggestion="Start a new task when ready",
        actions=[
            ErrorAction("Start New Task", "new_conversation", highlight=True),
        ],
        technical_details=str(error),
        error_code="USER_CANCELLED",
        can_retry=False,
        reassurance="Everything is safe - nothing was changed."
    )


# Comprehensive error mapping
ERROR_FORMATTERS = {
    LLMNoResponseError: format_llm_no_response_error,
    LLMContextWindowExceedError: format_context_window_error,
    AgentStuckInLoopError: format_agent_stuck_error,
    AgentRuntimeUnavailableError: format_runtime_unavailable_error,
    FunctionCallValidationError: format_function_call_error,
    FunctionCallNotExistsError: format_function_call_error,
    LLMMalformedActionError: format_malformed_action_error,
    UserCancelledError: format_user_cancelled_error,
}


def format_error_for_user(
    error: Exception,
    context: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Format any error into a user-friendly response.
    
    This is the main entry point for error formatting.
    
    Args:
        error: The exception to format
        context: Optional context (user_id, conversation_id, etc.)
        
    Returns:
        User-friendly error dict ready for JSON response
    """
    error_type = type(error)
    
    # Log the error for monitoring
    logger.error(
        f"Error occurred: {error_type.__name__} - {str(error)}",
        extra={"context": context or {}}
    )
    
    # Try to find a specific formatter
    if error_type in ERROR_FORMATTERS:
        formatter = ERROR_FORMATTERS[error_type]
        user_error = formatter(error)
        
        # Add context if provided
        if context:
            user_error.metadata.update(context)
        
        return user_error.to_dict()
    
    # Check for common error patterns in the message
    error_message = str(error).lower()
    
    # Rate limiting errors
    if "rate limit" in error_message or "too many requests" in error_message:
        return format_rate_limit_error(error, context).to_dict()
    
    # Authentication errors
    if "authentication" in error_message or "unauthorized" in error_message or "invalid token" in error_message:
        return format_authentication_error(error, context).to_dict()
    
    # Network errors
    if "connection" in error_message or "timeout" in error_message or "network" in error_message:
        return format_network_error(error, context).to_dict()
    
    # File errors
    if "file not found" in error_message or "no such file" in error_message:
        return format_file_not_found_error(error, context).to_dict()
    
    # Permission errors
    if "permission denied" in error_message or "forbidden" in error_message:
        return format_permission_error(error, context).to_dict()
    
    # Fallback: Generic user-friendly error
    return format_generic_error(error, context).to_dict()


def format_rate_limit_error(error: Exception, context: Optional[dict[str, Any]] = None) -> UserFriendlyError:
    """Format rate limiting errors."""
    # Try to extract reset time from error message
    reset_time = None
    if context and "reset_time" in context:
        reset_time = context["reset_time"]
    
    time_remaining = "a few minutes"
    if reset_time:
        try:
            reset_dt = datetime.fromisoformat(reset_time)
            delta = reset_dt - datetime.utcnow()
            minutes = max(1, int(delta.total_seconds() / 60))
            time_remaining = f"{minutes} minute{'s' if minutes != 1 else ''}"
        except Exception:
            pass
    
    return UserFriendlyError(
        title="You're going too fast!",
        message=(
            f"You've used all your requests for this period.\n\n"
            f"**Your quota resets in:** {time_remaining}\n\n"
            f"**Options:**\n"
            f"• Wait for your quota to reset\n"
            f"• Upgrade to Pro for higher limits\n"
            f"• Use a different account"
        ),
        severity=ErrorSeverity.WARNING,
        category=ErrorCategory.RATE_LIMIT,
        icon="⏰",
        suggestion=f"Wait {time_remaining} or upgrade to Pro",
        actions=[
            ErrorAction("Upgrade to Pro", "upgrade", url="/billing", highlight=True),
            ErrorAction("See Pricing", "pricing", url="/pricing"),
        ],
        technical_details=str(error),
        error_code="RATE_LIMIT_EXCEEDED",
        can_retry=True,
        retry_delay=300,  # 5 minutes
        help_url="https://docs.forge.ai/billing/rate-limits"
    )


def format_authentication_error(error: Exception, context: Optional[dict[str, Any]] = None) -> UserFriendlyError:
    """Format authentication errors."""
    return UserFriendlyError(
        title="Please sign in again",
        message=(
            "Your session has expired for security reasons.\n\n"
            "This happens after:\n"
            "• Being inactive for 24 hours\n"
            "• Logging in from a different device\n"
            "• Changing your password or API keys\n\n"
            "**Don't worry** - your conversations and work are saved!"
        ),
        severity=ErrorSeverity.WARNING,
        category=ErrorCategory.AUTHENTICATION,
        icon="🔒",
        suggestion="Sign in to continue",
        actions=[
            ErrorAction("Sign In", "login", url="/login", highlight=True),
        ],
        technical_details=str(error),
        error_code="AUTHENTICATION_REQUIRED",
        can_retry=False,
        help_url="https://docs.forge.ai/auth/sessions",
        reassurance="Your work is safe and saved"
    )


def format_network_error(error: Exception, context: Optional[dict[str, Any]] = None) -> UserFriendlyError:
    """Format network/connection errors."""
    return UserFriendlyError(
        title="Connection problem",
        message=(
            "We couldn't reach the server. This usually means:\n\n"
            "• Your internet connection hiccupped\n"
            "• The server is temporarily unavailable\n"
            "• A firewall is blocking the request\n\n"
            "**Quick fix:** Check your internet and try again."
        ),
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.NETWORK,
        icon="📡",
        suggestion="Check your connection and retry",
        actions=[
            ErrorAction("Retry", "retry", highlight=True),
            ErrorAction("Check Status", "status", url="https://status.forge.ai"),
        ],
        technical_details=str(error),
        error_code="NETWORK_ERROR",
        can_retry=True,
        retry_delay=5,
        help_url="https://docs.forge.ai/troubleshooting/connection"
    )


def format_file_not_found_error(error: Exception, context: Optional[dict[str, Any]] = None) -> UserFriendlyError:
    """Format file not found errors."""
    # Try to extract filename from error
    filename = "the file"
    error_str = str(error)
    if "'" in error_str:
        parts = error_str.split("'")
        if len(parts) >= 2:
            filename = f"'{parts[1]}'"
    
    return UserFriendlyError(
        title="File not found",
        message=(
            f"I couldn't find {filename} in your workspace.\n\n"
            f"**Did you mean to:**\n"
            f"• Create a new file with this name?\n"
            f"• Use a different filename?\n"
            f"• Check if it's in a different folder?\n\n"
            f"**Tip:** Use 'ls' or 'find' to search for files."
        ),
        severity=ErrorSeverity.WARNING,
        category=ErrorCategory.USER_INPUT,
        icon="📁",
        suggestion="Check the filename and path",
        actions=[
            ErrorAction("Create File", "create_file", highlight=True),
            ErrorAction("Search Files", "search_files"),
        ],
        technical_details=str(error),
        error_code="FILE_NOT_FOUND",
        can_retry=True
    )


def format_permission_error(error: Exception, context: Optional[dict[str, Any]] = None) -> UserFriendlyError:
    """Format permission denied errors."""
    return UserFriendlyError(
        title="Permission denied",
        message=(
            "You don't have permission to perform this action.\n\n"
            "This could mean:\n"
            "• The file is read-only\n"
            "• You need admin privileges\n"
            "• The folder is protected\n\n"
            "**Solutions:**\n"
            "• Check file permissions with 'ls -la'\n"
            "• Try with sudo (if appropriate)\n"
            "• Choose a different file or folder"
        ),
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.SYSTEM,
        icon="🔐",
        suggestion="Check file permissions",
        actions=[
            ErrorAction("Try Different File", "retry", highlight=True),
            ErrorAction("Learn More", "help", url="https://docs.forge.ai/permissions"),
        ],
        technical_details=str(error),
        error_code="PERMISSION_DENIED",
        can_retry=False
    )


def format_generic_error(error: Exception, context: Optional[dict[str, Any]] = None) -> UserFriendlyError:
    """Format generic/unmapped errors."""
    error_type = type(error).__name__
    
    return UserFriendlyError(
        title="Something went wrong",
        message=(
            "An unexpected error occurred. We're sorry about that!\n\n"
            "**What you can try:**\n"
            "• Refresh the page and try again\n"
            "• Start a new conversation\n"
            "• Check if your internet connection is stable\n\n"
            "**If this keeps happening:**\n"
            "• Take a screenshot of the error\n"
            "• Contact support with details\n"
            "• We'll fix it ASAP!"
        ),
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.SYSTEM,
        icon="❌",
        suggestion="Refresh and try again",
        actions=[
            ErrorAction("Refresh Page", "refresh", highlight=True),
            ErrorAction("New Session", "new_conversation"),
            ErrorAction("Contact Support", "support", url="mailto:support@forge.ai"),
        ],
        technical_details=f"{error_type}: {str(error)}",
        error_code=error_type.upper(),
        can_retry=True,
        help_url="https://docs.forge.ai/troubleshooting"
    )


def format_budget_exceeded_error(budget_info: Optional[dict[str, Any]] = None) -> UserFriendlyError:
    """Format budget exceeded errors."""
    budget = budget_info.get("budget", "$20.00") if budget_info else "$20.00"
    spend = budget_info.get("spend", budget) if budget_info else budget
    
    return UserFriendlyError(
        title="Budget limit reached",
        message=(
            f"You've reached your spending limit for this period.\n\n"
            f"**Current usage:** {spend} / {budget}\n\n"
            f"**What you can do:**\n"
            f"• Upgrade to a higher plan\n"
            f"• Wait for your budget to reset (usually monthly)\n"
            f"• Contact us for a custom plan\n\n"
            f"**Why limits exist:** We want to prevent surprise bills!"
        ),
        severity=ErrorSeverity.WARNING,
        category=ErrorCategory.RATE_LIMIT,
        icon="💰",
        suggestion="Upgrade your plan",
        actions=[
            ErrorAction("Upgrade Plan", "upgrade", url="/billing", highlight=True),
            ErrorAction("See Pricing", "pricing", url="/pricing"),
            ErrorAction("Contact Sales", "sales", url="mailto:sales@forge.ai"),
        ],
        technical_details=f"Budget exceeded: {spend} > {budget}",
        error_code="BUDGET_EXCEEDED",
        can_retry=False,
        help_url="https://docs.forge.ai/billing/budgets",
        reassurance="Your work is saved - just upgrade to continue!"
    )


# Helper function for graceful error handling
def safe_format_error(error: Exception, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Safely format error with fallback to generic error.
    
    This never raises an exception - even if formatting fails.
    
    Args:
        error: Exception to format
        context: Optional context
        
    Returns:
        User-friendly error dict (guaranteed)
    """
    try:
        return format_error_for_user(error, context)
    except Exception as formatting_error:
        logger.error(f"Error formatting error (meta!): {formatting_error}")
        
        # Ultra-safe fallback
        return {
            "title": "Unexpected error",
            "message": "Something went wrong. Please refresh and try again, or contact support.",
            "severity": "error",
            "category": "system",
            "icon": "❌",
            "suggestion": "Refresh the page",
            "actions": [
                {"label": "Refresh", "type": "refresh", "highlight": True},
                {"label": "Support", "type": "support", "url": "mailto:support@forge.ai"}
            ],
            "technical_details": f"{type(error).__name__}: {str(error)}",
            "error_code": "FORMATTING_FAILED",
            "can_retry": True
        }

