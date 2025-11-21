"""Public routes exposing available models, agents, and server metadata."""

from typing import Any

from fastapi import APIRouter

# Import agenthub to register all agents
import forge.agenthub  # noqa: F401
from forge.controller.agent import Agent
from forge.security.options import SecurityAnalyzers
from forge.server.dependencies import get_dependencies
from forge.server.shared import config, server_config
from forge.utils.llm import get_supported_llm_models

app = APIRouter(prefix="/api/options", dependencies=get_dependencies())


@app.get("/models")
async def get_litellm_models() -> list[str]:
    """Get all language models supported by LiteLLM and Bedrock.

    Retrieves a comprehensive list of available LLM models supported by
    LiteLLM integration and AWS Bedrock, excluding error-prone Bedrock
    models. Results are deduplicated and sorted alphabetically.

    Returns:
        list[str]: A sorted list of unique model identifiers (e.g.,
            ["gpt-4", "gpt-3.5-turbo", "claude-2", "llama-2-70b"]).

    Examples:
        >>> curl http://localhost:3000/api/options/models
        ["claude-2", "claude-instant-1", "gpt-3.5-turbo", "gpt-4", ...]

    Notes:
        - Results are cached and deduplicated
        - Bedrock models known to cause issues are filtered out
        - Requires LiteLLM and Bedrock configuration

    """
    return get_supported_llm_models(config)


@app.get("/agents")
async def get_agents() -> list[str]:
    """Get all available AI agents supported by the system.

    Retrieves a list of all registered agent implementations. Agents are
    automatically discovered and registered via the agenthub module import.

    Returns:
        list[str]: A sorted list of agent names available for selection
            (e.g., ["gpt-4-agent", "codebase-agent", "research-agent"]).

    Examples:
        >>> curl http://localhost:3000/api/options/agents
        ["agent-1", "agent-2", "code-analyzer-agent", ...]

    Notes:
        - Agents are auto-registered from forge.agenthub module
        - List includes both default and custom agents

    """
    return sorted(Agent.list_agents())


@app.get("/security-analyzers")
async def get_security_analyzers() -> list[str]:
    """Get all supported security analyzers.

    Retrieves a list of all security analysis tools available for analyzing
    code security issues, vulnerabilities, and compliance concerns.

    Returns:
        list[str]: A sorted list of security analyzer names (e.g.,
            ["semgrep", "bandit", "sonarqube"]).

    Examples:
        >>> curl http://localhost:3000/api/options/security-analyzers
        ["bandit", "semgrep", "sonarqube", ...]

    Notes:
        - Security analyzers must be initialized per-conversation
        - Availability depends on system configuration

    """
    return sorted(SecurityAnalyzers.keys())


@app.get("/config")
async def get_config() -> dict[str, Any]:
    """Get current server configuration and settings.

    Retrieves the complete active server configuration including deployment
    mode, feature flags, API settings, and other runtime parameters.

    Returns:
        dict[str, Any]: Dictionary containing all active configuration parameters
            with structure depending on server_config implementation:
            - app_mode: Application mode ("SAAS", "STANDALONE", etc.)
            - api_base_url: Base URL for API endpoints
            - workspace_base: Base path for workspace directory
            - feature_flags: Enabled features
            - Other server-specific settings

    Examples:
        >>> curl http://localhost:3000/api/options/config
        {
            "app_mode": "SAAS",
            "api_base_url": "https://api.example.com",
            "workspace_base": "/data/workspace",
            ...
        }

    Notes:
        - This is a public endpoint; sensitive credentials are not included
        - Configuration is cached in server_config singleton

    """
    return server_config.get_config()
