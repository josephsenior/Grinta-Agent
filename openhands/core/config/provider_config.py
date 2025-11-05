"""
Production-ready LLM provider configuration system.

This module provides a declarative, provider-aware configuration system that ensures
proper parameter handling for all LLM providers while maintaining flexibility for
custom and unknown providers.
"""

from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum

from openhands.core.logger import openhands_logger as logger


class ParameterType(Enum):
    """Types of parameters for provider validation."""
    REQUIRED = "required"
    OPTIONAL = "optional" 
    FORBIDDEN = "forbidden"


@dataclass
class ProviderConfig:
    """Configuration schema for an LLM provider."""
    
    # Core provider identification
    name: str
    env_var: Optional[str] = None
    requires_protocol: bool = True  # Whether base_url needs http(s)://
    supports_streaming: bool = True
    
    # Parameter definitions
    required_params: Set[str] = None
    optional_params: Set[str] = None
    forbidden_params: Set[str] = None
    
    # API key format validation
    api_key_prefixes: List[str] = None
    api_key_min_length: int = 10
    
    # Special handling flags
    handles_own_routing: bool = False  # Provider handles routing internally
    requires_custom_llm_provider: bool = False
    
    def __post_init__(self):
        """Ensure sets are initialized properly."""
        if self.required_params is None:
            self.required_params = set()
        if self.optional_params is None:
            self.optional_params = set()
        if self.forbidden_params is None:
            self.forbidden_params = set()
        if self.api_key_prefixes is None:
            self.api_key_prefixes = []

    def is_param_allowed(self, param_name: str) -> bool:
        """Check if a parameter is allowed for this provider."""
        return (param_name not in self.forbidden_params and 
                (param_name in self.required_params or param_name in self.optional_params))

    def is_param_required(self, param_name: str) -> bool:
        """Check if a parameter is required for this provider."""
        return param_name in self.required_params

    def validate_base_url(self, base_url: Optional[str]) -> Optional[str]:
        """Validate and normalize base_url for this provider."""
        if not base_url:
            return None
            
        base_url = str(base_url).strip()
        if not base_url:
            return None
            
        # If provider handles its own routing, don't use custom base_url
        if self.handles_own_routing:
            logger.debug(f"Provider {self.name} handles own routing - clearing base_url")
            return None
            
        # Check protocol requirement
        if self.requires_protocol and not any(base_url.startswith(proto) for proto in ['http://', 'https://']):
            logger.warning(f"Provider {self.name} requires base_url with protocol - clearing invalid URL: {base_url}")
            return None
            
        return base_url


class ProviderConfigurationManager:
    """Manages provider configurations and provides validation logic."""
    
    def __init__(self):
        """Initialize with comprehensive provider configurations."""
        self._provider_configs = self._load_provider_configurations()
        self._unknown_provider_config = self._create_unknown_provider_config()

    def _load_provider_configurations(self) -> Dict[str, ProviderConfig]:
        """Load provider-specific configurations based on LiteLLM requirements."""
        configs = {}
        
        # OpenHands - handles routing internally to multiple providers
        configs['openhands'] = ProviderConfig(
            name='openhands',
            env_var='LLM_API_KEY',
            requires_protocol=False,
            supports_streaming=True,
            required_params={'api_key', 'model'},
            optional_params={'timeout', 'temperature', 'max_tokens', 'top_p', 'seed', 'drop_params'},
            forbidden_params={'base_url', 'custom_llm_provider', 'api_version'},
            api_key_prefixes=['sk-'],  # OpenHands uses sk- prefix
            api_key_min_length=15,
            handles_own_routing=True,
            requires_custom_llm_provider=False
        )
        
        # OpenRouter - handles routing internally, very sensitive to extra params
        configs['openrouter'] = ProviderConfig(
            name='openrouter',
            env_var='OPENROUTER_API_KEY',
            requires_protocol=False,
            supports_streaming=True,
            required_params={'api_key', 'model'},
            optional_params={'timeout', 'temperature', 'max_tokens', 'top_p', 'seed', 'drop_params'},
            forbidden_params={'base_url', 'custom_llm_provider', 'api_version'},
            api_key_prefixes=['sk-or-'],
            api_key_min_length=15,
            handles_own_routing=True,
            requires_custom_llm_provider=False
        )
        
        # OpenAI - supports custom base_url, standard parameters
        configs['openai'] = ProviderConfig(
            name='openai',
            env_var='OPENAI_API_KEY',
            requires_protocol=True,
            supports_streaming=True,
            required_params={'api_key', 'model'},
            optional_params={'base_url', 'api_version', 'timeout', 'temperature', 'max_tokens', 
                           'top_p', 'seed', 'drop_params', 'custom_llm_provider'},
            forbidden_params=set(),
            api_key_prefixes=['sk-'],
            api_key_min_length=20,
            handles_own_routing=False,
            requires_custom_llm_provider=False
        )
        
        # Anthropic - standard setup, no custom base_url typically
        configs['anthropic'] = ProviderConfig(
            name='anthropic',
            env_var='ANTHROPIC_API_KEY',
            requires_protocol=True,
            supports_streaming=True,
            required_params={'api_key', 'model'},
            optional_params={'timeout', 'temperature', 'max_tokens', 'seed', 'drop_params'},
            forbidden_params={'custom_llm_provider'},  # Usually not needed
            api_key_prefixes=['sk-ant-'],
            api_key_min_length=20,
            handles_own_routing=False,
            requires_custom_llm_provider=False
        )
        
        # Google/Gemini - special handling for base_url
        configs['google'] = ProviderConfig(
            name='google',
            env_var='GEMINI_API_KEY',
            requires_protocol=False,  # Can work with various formats
            supports_streaming=True,
            required_params={'api_key', 'model'},
            optional_params={'timeout', 'temperature', 'max_tokens', 'seed', 'drop_params'},
            forbidden_params={'custom_llm_provider', 'base_url'},  # Let LiteLLM handle routing
            api_key_prefixes=['AIza'],
            api_key_min_length=20,
            handles_own_routing=True,
            requires_custom_llm_provider=False
        )
        
        # Mistral - standard setup
        configs['mistral'] = ProviderConfig(
            name='mistral',
            env_var='MISTRAL_API_KEY',
            requires_protocol=True,
            supports_streaming=True,
            required_params={'api_key', 'model'},
            optional_params={'base_url', 'timeout', 'temperature', 'max_tokens', 'seed', 'drop_params'},
            forbidden_params={'custom_llm_provider'},
            api_key_prefixes=['mistral-'],
            api_key_min_length=20,
            handles_own_routing=False,
            requires_custom_llm_provider=False
        )
        
        # Groq - standard setup
        configs['groq'] = ProviderConfig(
            name='groq',
            env_var='GROQ_API_KEY',
            requires_protocol=True,
            supports_streaming=True,
            required_params={'api_key', 'model'},
            optional_params={'base_url', 'timeout', 'temperature', 'max_tokens', 'seed', 'drop_params'},
            forbidden_params={'custom_llm_provider'},
            api_key_prefixes=['gsk_'],
            api_key_min_length=20,
            handles_own_routing=False,
            requires_custom_llm_provider=False
        )
        
        # Together AI
        configs['together'] = ProviderConfig(
            name='together',
            env_var='TOGETHER_API_KEY',
            requires_protocol=True,
            supports_streaming=True,
            required_params={'api_key', 'model'},
            optional_params={'base_url', 'timeout', 'temperature', 'max_tokens', 'seed', 'drop_params'},
            forbidden_params={'custom_llm_provider'},
            api_key_prefixes=['sk-'],
            api_key_min_length=20,
            handles_own_routing=False,
            requires_custom_llm_provider=False
        )
        
        # DeepInfra
        configs['deepinfra'] = ProviderConfig(
            name='deepinfra',
            env_var='DEEPINFRA_API_KEY',
            requires_protocol=True,
            supports_streaming=True,
            required_params={'api_key', 'model'},
            optional_params={'base_url', 'timeout', 'temperature', 'max_tokens', 'seed', 'drop_params'},
            forbidden_params={'custom_llm_provider'},
            api_key_prefixes=['r8_'],
            api_key_min_length=20,
            handles_own_routing=False,
            requires_custom_llm_provider=False
        )
        
        # Replicate
        configs['replicate'] = ProviderConfig(
            name='replicate',
            env_var='REPLICATE_API_KEY',
            requires_protocol=True,
            supports_streaming=False,  # Replicate doesn't support streaming typically
            required_params={'api_key', 'model'},
            optional_params={'timeout', 'temperature', 'max_tokens', 'seed', 'drop_params'},
            forbidden_params={'base_url', 'custom_llm_provider', 'stream'},
            api_key_prefixes=['r8_'],
            api_key_min_length=20,
            handles_own_routing=True,
            requires_custom_llm_provider=False
        )
        
        # Fireworks AI
        configs['fireworks'] = ProviderConfig(
            name='fireworks',
            env_var='FIREWORKS_API_KEY',
            requires_protocol=True,
            supports_streaming=True,
            required_params={'api_key', 'model'},
            optional_params={'base_url', 'timeout', 'temperature', 'max_tokens', 'seed', 'drop_params'},
            forbidden_params={'custom_llm_provider'},
            api_key_prefixes=['fk-'],
            api_key_min_length=20,
            handles_own_routing=False,
            requires_custom_llm_provider=False
        )
        
        # Perplexity
        configs['perplexity'] = ProviderConfig(
            name='perplexity',
            env_var='PERPLEXITY_API_KEY',
            requires_protocol=True,
            supports_streaming=True,
            required_params={'api_key', 'model'},
            optional_params={'base_url', 'timeout', 'temperature', 'max_tokens', 'seed', 'drop_params'},
            forbidden_params={'custom_llm_provider'},
            api_key_prefixes=['pplx-'],
            api_key_min_length=20,
            handles_own_routing=False,
            requires_custom_llm_provider=False
        )
        
        # Cohere
        configs['cohere'] = ProviderConfig(
            name='cohere',
            env_var='COHERE_API_KEY',
            requires_protocol=True,
            supports_streaming=True,
            required_params={'api_key', 'model'},
            optional_params={'base_url', 'timeout', 'temperature', 'max_tokens', 'seed', 'drop_params'},
            forbidden_params={'custom_llm_provider'},
            api_key_prefixes=['co-'],
            api_key_min_length=20,
            handles_own_routing=False,
            requires_custom_llm_provider=False
        )
        
        # Ollama - special case, often no API key needed
        configs['ollama'] = ProviderConfig(
            name='ollama',
            env_var=None,
            requires_protocol=True,
            supports_streaming=True,
            required_params={'base_url', 'model'},  # base_url is critical for Ollama
            optional_params={'timeout', 'temperature', 'max_tokens', 'seed', 'drop_params'},
            forbidden_params={'api_key', 'custom_llm_provider'},  # API key usually not needed
            api_key_prefixes=[],
            api_key_min_length=0,
            handles_own_routing=False,
            requires_custom_llm_provider=True  # Ollama often needs explicit provider
        )
        
        return configs

    def _create_unknown_provider_config(self) -> ProviderConfig:
        """Create a safe default configuration for unknown providers."""
        return ProviderConfig(
            name='unknown',
            env_var=None,
            requires_protocol=True,
            supports_streaming=False,  # Conservative default
            required_params={'model'},  # Only model is always required
            optional_params={'api_key', 'base_url', 'timeout', 'temperature', 'max_tokens', 
                           'top_p', 'seed', 'drop_params', 'api_version'},
            forbidden_params=set(),  # Don't forbid anything for unknown providers
            api_key_prefixes=[],
            api_key_min_length=10,
            handles_own_routing=False,
            requires_custom_llm_provider=False
        )

    def get_provider_config(self, provider: str) -> ProviderConfig:
        """Get configuration for a provider, falling back to unknown provider config."""
        return self._provider_configs.get(provider.lower(), self._unknown_provider_config)

    def validate_and_clean_params(self, provider: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean parameters for a specific provider.
        
        Args:
            provider: The LLM provider name
            params: Dictionary of parameters to validate and clean
            
        Returns:
            Cleaned dictionary with only valid parameters for the provider
        """
        config = self.get_provider_config(provider)
        cleaned_params = {}
        warnings = []
        
        logger.debug(f"Validating parameters for provider: {provider}")
        
        # Process each parameter
        for param_name, param_value in params.items():
            if param_name in config.forbidden_params:
                logger.debug(f"Removing forbidden parameter '{param_name}' for provider {provider}")
                warnings.append(f"Parameter '{param_name}' is not allowed for {provider} provider")
                continue
                
            if param_name in config.required_params or param_name in config.optional_params:
                # Special handling for base_url
                if param_name == 'base_url':
                    cleaned_value = config.validate_base_url(param_value)
                    if cleaned_value is not None:
                        cleaned_params[param_name] = cleaned_value
                    elif param_value is not None:
                        logger.debug(f"Cleaned base_url for {provider}: {param_value} -> None")
                else:
                    cleaned_params[param_name] = param_value
            else:
                # Parameter not in config - allow it for flexibility (unknown providers)
                if provider == 'unknown':
                    cleaned_params[param_name] = param_value
                    logger.debug(f"Allowing unknown parameter '{param_name}' for unknown provider")
                else:
                    logger.debug(f"Parameter '{param_name}' not specified for {provider} provider - allowing for flexibility")
                    cleaned_params[param_name] = param_value
        
        # Validate required parameters are present
        missing_required = config.required_params - set(cleaned_params.keys())
        if missing_required:
            warnings.append(f"Missing required parameters for {provider}: {', '.join(missing_required)}")
        
        if warnings:
            logger.warning(f"Parameter validation warnings for {provider}: {'; '.join(warnings)}")
        
        logger.debug(f"Parameter validation complete for {provider}: {len(cleaned_params)} params kept")
        return cleaned_params

    def validate_api_key_format(self, provider: str, api_key: Optional[str]) -> bool:
        """
        Validate API key format for a provider.
        
        Args:
            provider: The LLM provider name
            api_key: The API key to validate
            
        Returns:
            True if the API key format is valid or acceptable
        """
        if not api_key:
            config = self.get_provider_config(provider)
            return 'api_key' not in config.required_params
        
        config = self.get_provider_config(provider)
        
        # Check minimum length
        if len(api_key) < config.api_key_min_length:
            logger.warning(f"API key for {provider} is shorter than expected minimum ({config.api_key_min_length})")
            return False
        
        # Check prefixes if specified - warn but don't fail validation
        if config.api_key_prefixes:
            if not any(api_key.startswith(prefix) for prefix in config.api_key_prefixes):
                logger.warning(f"API key for {provider} doesn't match expected prefixes: {config.api_key_prefixes}")
                # Don't return False here - just warn and continue
                # This allows for API key variations and updates from providers
        
        return True

    def get_environment_variable(self, provider: str) -> Optional[str]:
        """Get the environment variable name for a provider."""
        config = self.get_provider_config(provider)
        return config.env_var


# Global instance for use throughout the application
provider_config_manager = ProviderConfigurationManager()
