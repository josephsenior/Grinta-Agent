"""Interactive prompts and helpers for configuring Forge CLI settings."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.completion import FuzzyWordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import print_container
from prompt_toolkit.widgets import Frame, TextArea
from pydantic import SecretStr

from forge.cli.pt_style import COLOR_GREY, get_cli_style
from forge.cli.tui import UserCancelledError, cli_confirm, kb_cancel
from forge.cli.utils import (
    VERIFIED_ANTHROPIC_MODELS,
    VERIFIED_MISTRAL_MODELS,
    VERIFIED_OPENAI_MODELS,
    VERIFIED_OPENHANDS_MODELS,
    VERIFIED_PROVIDERS,
    extract_model_and_provider,
    organize_models_and_providers,
)
from forge.controller.agent import Agent
from forge.core.config.condenser_config import (  # noqa: F401
    CondenserPipelineConfig,
    ConversationWindowCondenserConfig,
    NoOpCondenserConfig,
)
from forge.core.config.config_utils import OH_DEFAULT_AGENT
from forge.memory.condenser.impl.llm_summarizing_condenser import (
    LLMSummarizingCondenserConfig,
)
from forge.storage.data_models.settings import Settings
from forge.utils.llm import get_supported_llm_models

if TYPE_CHECKING:
    from forge.core.config import ForgeConfig
    from forge.storage.settings.file_settings_store import FileSettingsStore


PROVIDER_DISPLAY_NAMES = {
    "openhands": "Openhands",
    "forge": "Openhands",  # Legacy alias
}

# Maintain backwards compatibility with legacy Forge naming.
VERIFIED_FORGE_MODELS = VERIFIED_OPENHANDS_MODELS


def _normalize_provider(provider: str | None) -> str:
    """Normalize provider identifiers, handling legacy aliases."""
    if not provider:
        return ""
    return "openhands" if provider.lower() == "forge" else provider


def _get_llm_settings_labels(llm_config) -> list[tuple[str, str]]:
    """Get LLM-related settings labels and values."""
    advanced_llm_settings = bool(llm_config.base_url)

    if advanced_llm_settings:
        return [
            ("   Custom Model", str(llm_config.model)),
            ("   Base URL", str(llm_config.base_url)),
            ("   API Key", "********" if llm_config.api_key else "Not Set"),
        ]
    provider = getattr(llm_config, "provider", llm_config.model.split("/")[0] if "/" in llm_config.model else "Unknown")
    return [
        ("   LLM Provider", str(provider)),
        ("   LLM Model", str(llm_config.model)),
        ("   API Key", "********" if llm_config.api_key else "Not Set"),
    ]


def _format_provider_display_name(provider: str) -> str:
    """Format provider name for display and persisted settings."""
    if not provider:
        return provider
    return PROVIDER_DISPLAY_NAMES.get(provider, provider)


def _get_general_settings_labels(config: ForgeConfig) -> list[tuple[str, str]]:
    """Get general settings labels and values."""
    return [
        ("   Agent", str(config.default_agent)),
        ("   Confirmation Mode", "Enabled" if config.security.confirmation_mode else "Disabled"),
        ("   Memory Condensation", "Enabled" if config.enable_default_condenser else "Disabled"),
        ("   Search API Key", "********" if config.search_api_key else "Not Set"),
        ("   Configuration File", str(Path(config.file_store_path) / "settings.json")),
    ]


def _format_settings_display(labels_and_values: list[tuple[str, str]]) -> str:
    """Format settings for display with proper alignment."""
    str_labels_and_values = [(label, str(value)) for label, value in labels_and_values]
    max_label_width = max((len(label) for label, _ in str_labels_and_values), default=0)
    settings_lines = [f"{f'{label}:':<{max_label_width + 1}} {value:<}" for label, value in str_labels_and_values]
    return "\n".join(settings_lines)


def display_settings(config: ForgeConfig) -> None:
    """Display current Forge configuration settings.
    
    Shows LLM settings, general configuration, and runtime options.
    
    Args:
        config: Forge configuration to display

    """
    llm_config = config.get_llm_config()

    labels_and_values = []
    labels_and_values.extend(_get_llm_settings_labels(llm_config))
    labels_and_values.extend(_get_general_settings_labels(config))

    settings_text = _format_settings_display(labels_and_values)
    container = Frame(
        TextArea(text=settings_text, read_only=True, style=COLOR_GREY, wrap_lines=True),
        title="Settings",
        style=f"fg:{COLOR_GREY}",
    )
    print_container(container)


async def get_validated_input(
    session: PromptSession,
    prompt_text: str,
    completer=None,
    validator=None,
    error_message: str = "Input cannot be empty",
    *,
    default_value: str = "",
    enter_keeps_value: str | None = None,
) -> str:
    """Get validated input from user.

    Args:
        session: PromptSession instance
        prompt_text: The text to display before the input
        completer: Completer instance
        validator: Function to validate input
        error_message: Error message to display if input is invalid
        default_value: Value to show prefilled in the prompt (prompt placeholder)
        enter_keeps_value: If provided, pressing Enter on an empty input will
            return this value (useful for keeping existing sensitive values)

    Returns:
        str: The validated input

    """
    session.completer = completer
    session.completer = completer
    value = None
    while True:
        value = await session.prompt_async(prompt_text, default=default_value)
        if not value.strip() and enter_keeps_value is not None:
            value = enter_keeps_value
        if validator:
            is_valid = validator(value)
            if not is_valid:
                print_formatted_text("")
                print_formatted_text(HTML(f"<grey>{error_message}: {value}</grey>"))
                print_formatted_text("")
                continue
        elif not value:
            print_formatted_text("")
            print_formatted_text(HTML(f"<grey>{error_message}</grey>"))
            print_formatted_text("")
            continue
        break
    return value


def save_settings_confirmation(config: ForgeConfig) -> bool:
    """Prompt user to confirm saving settings changes.
    
    Args:
        config: Forge configuration for dialog
        
    Returns:
        True if user confirmed save

    """
    return (
        cli_confirm(config, "\nSave new settings? (They will take effect after restart)", ["Yes, save", "No, discard"])
        == 0
    )


def _get_current_values_for_modification_basic(config: ForgeConfig) -> tuple[str, str, str]:
    llm_config = config.get_llm_config()
    current_provider = ""
    current_model = ""
    current_api_key = llm_config.api_key.get_secret_value() if llm_config.api_key else ""
    if llm_config.model:
        model_info = extract_model_and_provider(llm_config.model)
        current_provider = _normalize_provider(model_info.provider)
        current_model = model_info.model or ""
    return (current_provider, current_model, current_api_key)


def _get_default_provider(provider_list: list[str]) -> str:
    if "anthropic" in provider_list:
        return "anthropic"
    return provider_list[0] if provider_list else ""


def _find_provider_in_verified(
    verified_providers: list[str],
    current_provider: str,
    default_provider: str,
) -> int | None:
    """Find provider index in verified providers list."""
    target_provider = current_provider or default_provider
    if target_provider in verified_providers:
        return verified_providers.index(target_provider)
    return None


def _get_initial_provider_index(
    verified_providers: list[str],
    current_provider: str,
    default_provider: str,
    provider_choices: list[str],
) -> int:
    # Try to find in verified providers first
    verified_index = _find_provider_in_verified(verified_providers, current_provider, default_provider)
    if verified_index is not None:
        return verified_index

    # If provider exists but not in verified, select "other" option
    return len(provider_choices) - 1 if current_provider or default_provider else 0


def _get_initial_model_index(verified_models: list[str], current_model: str, default_model: str) -> int:
    if (current_model or default_model) in verified_models:
        return verified_models.index(current_model or default_model)
    return 0


def _prepare_provider_lists(organized_models: dict) -> tuple[list[str], list[str], str]:
    """Prepare provider lists and determine default provider."""
    provider_list = list(organized_models.keys())
    verified_providers = [p for p in VERIFIED_PROVIDERS if p in provider_list]
    provider_list = [p for p in provider_list if p not in verified_providers]
    provider_list = verified_providers + provider_list
    default_provider = _get_default_provider(provider_list)
    return verified_providers, provider_list, default_provider


def _get_provider_choice_index(provider_choice) -> int:
    """Convert provider choice to index with error handling."""
    try:
        return int(provider_choice)
    except (TypeError, ValueError):
        return 0


def _get_fallback_provider(organized_models: dict) -> str:
    """Get fallback provider if selection is invalid."""
    return "anthropic" if "anthropic" in organized_models else next(iter(organized_models.keys()))


async def _select_provider(
    session: PromptSession,
    config: ForgeConfig,
    organized_models: dict,
    current_provider: str,
    provider_completer: FuzzyWordCompleter,
) -> str:
    """Select LLM provider with verified and custom options."""
    normalized_models = dict(organized_models)
    if "forge" in organized_models and "openhands" not in organized_models:
        normalized_models["openhands"] = organized_models["forge"]

    organized_models = normalized_models

    verified_providers, _provider_list, default_provider = _prepare_provider_lists(organized_models)

    print_formatted_text(HTML(f"\n<grey>Default provider: </grey><green>{default_provider}</green>"))
    provider_choices = [*verified_providers, "Select another provider"]
    provider_choice = cli_confirm(
        config,
        "(Step 1/3) Select LLM Provider:",
        provider_choices,
        initial_selection=_get_initial_provider_index(
            verified_providers,
            current_provider,
            default_provider,
            provider_choices,
        ),
    )

    choice_index = _get_provider_choice_index(provider_choice)

    if choice_index < len(verified_providers):
        provider = verified_providers[choice_index]
    else:
        default_value = current_provider if current_provider not in verified_providers else ""
        provider = await get_validated_input(
            session,
            "(Step 1/3) Select LLM Provider (TAB for options, CTRL-c to cancel): ",
            completer=provider_completer,
            validator=lambda x: x in organized_models,
            error_message="Invalid provider selected",
            default_value=default_value,
        )

    if provider not in organized_models:
        provider = _get_fallback_provider(organized_models)

    return provider


def _reorder_models_by_verified(provider: str, provider_models: list[str]) -> list[str]:
    """Reorder models to put verified models first."""
    if provider == "openai":
        verified_models = VERIFIED_OPENAI_MODELS
    elif provider == "anthropic":
        verified_models = VERIFIED_ANTHROPIC_MODELS
    elif provider == "mistral":
        verified_models = VERIFIED_MISTRAL_MODELS
    elif provider == "openhands":
        verified_models = VERIFIED_OPENHANDS_MODELS
    else:
        return provider_models

    # Remove verified models from the list and prepend them
    other_models = [m for m in provider_models if m not in verified_models]
    return verified_models + other_models


def _get_default_model_for_provider(provider: str, provider_models: list[str]) -> str:
    """Get the default model for a specific provider."""
    if provider == "anthropic" and VERIFIED_ANTHROPIC_MODELS:
        return VERIFIED_ANTHROPIC_MODELS[0]
    if provider == "openai" and VERIFIED_OPENAI_MODELS:
        return VERIFIED_OPENAI_MODELS[0]
    if provider == "mistral" and VERIFIED_MISTRAL_MODELS:
        return VERIFIED_MISTRAL_MODELS[0]
    if provider == "openhands" and VERIFIED_OPENHANDS_MODELS:
        return VERIFIED_OPENHANDS_MODELS[0]
    return provider_models[0] if provider_models else "claude-sonnet-4-20250514"


def _create_model_validator(provider: str, provider_models: list[str]):
    """Create a model validator function."""

    def model_validator(x) -> bool:
        """Validate model name input.
        
        Args:
            x: Model name to validate
            
        Returns:
            True if valid

        """
        if not x.strip():
            return False
        if x not in provider_models:
            print_formatted_text(
                HTML(
                    f"<yellow>Warning: {x} is not in the predefined list for provider {provider}. Make sure this model name is correct.</yellow>",
                ),
            )
        return True

    return model_validator


async def _select_openhands_model(
    session: PromptSession,
    config: ForgeConfig,
    current_model: str,
    default_model: str,
) -> str:
    """Select model for Openhands provider."""
    print_formatted_text(
        HTML(
            '\nYou can find your Openhands LLM API Key in the <a href="https://app.all-hands.dev/settings/api-keys">API Keys</a> tab of Openhands Cloud: https://app.all-hands.dev/settings/api-keys',
        ),
    )
    model_choices = VERIFIED_OPENHANDS_MODELS
    model_choice = cli_confirm(
        config,
        "(Step 2/3) Select Available Openhands Model:\n"
        "LLM usage is billed at the providers' rates with no markup. Details: https://docs.all-hands.dev/usage/llms/Forge-llms",
        model_choices,
        initial_selection=_get_initial_model_index(
            VERIFIED_OPENHANDS_MODELS,
            current_model,
            default_model),
    )
    return model_choices[model_choice]


async def _select_other_provider_model(
    session: PromptSession,
    config: ForgeConfig,
    provider: str,
    provider_models: list[str],
    current_model: str,
    default_model: str,
    *,
    show_default_hint: bool = True,
) -> str:
    """Select model for other providers."""
    if show_default_hint:
        print_formatted_text(HTML(f"\n<grey>Default model: </grey><green>{default_model}</green>"))

    change_model = (
        cli_confirm(
            config,
            "Do you want to use a different model?",
            [f"Use {default_model}", "Select another model"],
            initial_selection=0 if (current_model or default_model) == default_model else 1,
        )
        == 1
    )

    if change_model:
        model_completer = FuzzyWordCompleter(provider_models, WORD=True)
        model_validator = _create_model_validator(provider, provider_models)

        return await get_validated_input(
            session,
            "(Step 2/3) Select LLM Model (TAB for options, CTRL-c to cancel): ",
            completer=model_completer,
            validator=model_validator,
            error_message="Model name cannot be empty",
            default_value=current_model if current_model != default_model else "",
        )
    return default_model


async def _select_model(
    session: PromptSession,
    config: ForgeConfig,
    provider: str,
    organized_models: dict,
    current_model: str,
    *,
    suggested_model: str | None = None,
    show_default_hint: bool = True,
) -> str:
    """Select LLM model based on provider."""
    provider_models = organized_models[provider]["models"]
    provider_models = _reorder_models_by_verified(provider, provider_models)
    default_model = suggested_model or _get_default_model_for_provider(provider, provider_models)

    if provider == "openhands":
        return await _select_openhands_model(session, config, current_model, default_model)
    return await _select_other_provider_model(
        session,
        config,
        provider,
        provider_models,
        current_model,
        default_model,
        show_default_hint=show_default_hint,
    )


async def _get_api_key(session: PromptSession, config: ForgeConfig, provider: str, current_api_key: str) -> str:
    """Get API key input with provider-specific prompt."""
    if provider == "openhands":
        print_formatted_text(
            HTML(
                '\nYou can find your Openhands LLM API Key in the <a href="https://app.all-hands.dev/settings/api-keys">API Keys</a> tab of Openhands Cloud: https://app.all-hands.dev/settings/api-keys',
            ),
        )
    prompt_text = "(Step 3/3) Enter API Key (CTRL-c to cancel): "
    if current_api_key:
        prompt_text = f"(Step 3/3) Enter API Key [{current_api_key[:4]}***{current_api_key[-4:]}] (CTRL-c to cancel, ENTER to keep current, type new to change): "
    return await get_validated_input(
        session,
        prompt_text,
        error_message="API Key cannot be empty",
        default_value="",
        enter_keeps_value=current_api_key,
    )


async def modify_llm_settings_basic(config: ForgeConfig, settings_store: FileSettingsStore) -> None:
    """Modify basic LLM settings (provider, model, API key).
    
    Interactive wizard for changing core LLM configuration.
    
    Args:
        config: Forge configuration to modify
        settings_store: Settings storage backend

    """
    model_list = get_supported_llm_models(config)
    organized_models = organize_models_and_providers(model_list)
    current_provider, current_model, current_api_key = _get_current_values_for_modification_basic(config)
    provider_completer = FuzzyWordCompleter(list(organized_models.keys()), WORD=True)
    session = PromptSession(key_bindings=kb_cancel(), style=get_cli_style())
    provider = None
    model = None
    api_key = None
    try:
        provider = await _select_provider(session, config, organized_models, current_provider, provider_completer)
        if provider != current_provider:
            current_model = ""
            current_api_key = ""
        provider_display_name = _format_provider_display_name(provider)
        provider_info = organized_models.get(provider, {"models": [], "separator": "/"})
        provider_models = provider_info.get("models", [])
        # Set default model to the best verified model for the provider
        first_model_candidate = provider_models[0] if provider_models else None
        suggested_default_model = _get_default_model_for_provider(provider, provider_models)
        if suggested_default_model is None:
            suggested_default_model = first_model_candidate
        hint_already_displayed = False
        # Show the default model
        if suggested_default_model:
            print_formatted_text(
                HTML(f"\n<grey>Default model: </grey><green>{suggested_default_model}</green>"),
            )
            hint_already_displayed = True
        model = await _select_model(
            session,
            config,
            provider,
            organized_models,
            current_model,
            suggested_model=suggested_default_model,
            show_default_hint=not hint_already_displayed,
        )
        api_key = await _get_api_key(session, config, provider, current_api_key)
    except (UserCancelledError, KeyboardInterrupt, EOFError):
        return
    save_settings = save_settings_confirmation(config)
    if not save_settings:
        return
    llm_config = config.get_llm_config()
    separator = provider_info.get("separator", "/")
    model_identifier = f"{provider_display_name}{separator}{model}"
    llm_config.model = model_identifier
    llm_config.api_key = SecretStr(api_key)
    llm_config.base_url = None
    config.set_llm_config(llm_config)
    config.default_agent = OH_DEFAULT_AGENT
    config.enable_default_condenser = True
    agent_config = config.get_agent_config(config.default_agent)
    agent_config.condenser = LLMSummarizingCondenserConfig(llm_config=llm_config, type="llm")
    config.set_agent_config(agent_config, config.default_agent)
    settings = await settings_store.load() or Settings()
    settings.llm_model = model_identifier
    settings.llm_api_key = SecretStr(api_key)
    settings.llm_base_url = None
    settings.agent = OH_DEFAULT_AGENT
    settings.enable_default_condenser = True
    await settings_store.store(settings)


async def _collect_llm_settings_input(
    session: PromptSession,
    config: ForgeConfig,
    llm_config,
) -> tuple[str, str, str, str, bool, bool]:
    """Collect LLM settings input from user."""
    custom_model = await get_validated_input(
        session,
        "(Step 1/6) Custom Model (CTRL-c to cancel): ",
        error_message="Custom Model cannot be empty",
        default_value=llm_config.model or "",
    )

    base_url = await get_validated_input(
        session,
        "(Step 2/6) Base URL (CTRL-c to cancel): ",
        error_message="Base URL cannot be empty",
        default_value=llm_config.base_url or "",
    )

    api_key = await _get_api_key_input(session, llm_config)
    agent = await _get_agent_input(session, config)

    enable_confirmation_mode = (
        cli_confirm(
            config,
            question="(Step 5/6) Confirmation Mode (CTRL-c to cancel):",
            choices=["Enable", "Disable"],
            initial_selection=0 if config.security.confirmation_mode else 1,
        )
        == 0
    )

    enable_memory_condensation = (
        cli_confirm(
            config,
            question="(Step 6/6) Memory Condensation (CTRL-c to cancel):",
            choices=["Enable", "Disable"],
            initial_selection=0 if config.enable_default_condenser else 1,
        )
        == 0
    )

    return custom_model, base_url, api_key, agent, enable_confirmation_mode, enable_memory_condensation


async def _get_api_key_input(session: PromptSession, llm_config) -> str:
    """Get API key input from user with masked current value."""
    prompt_text = "(Step 3/6) API Key (CTRL-c to cancel): "
    current_api_key = llm_config.api_key.get_secret_value() if llm_config.api_key else ""

    if current_api_key:
        prompt_text = f"(Step 3/6) API Key [{current_api_key[:4]}***{current_api_key[-4:]}] (CTRL-c to cancel, ENTER to keep current, type new to change): "

    return await get_validated_input(
        session,
        prompt_text,
        error_message="API Key cannot be empty",
        default_value="",
        enter_keeps_value=current_api_key,
    )


async def _get_agent_input(session: PromptSession, config: ForgeConfig) -> str:
    """Get agent selection input from user."""
    agent_list = Agent.list_agents()
    agent_completer = FuzzyWordCompleter(agent_list, WORD=True)

    return await get_validated_input(
        session,
        "(Step 4/6) Agent (TAB for options, CTRL-c to cancel): ",
        completer=agent_completer,
        validator=lambda x: x in agent_list,
        error_message="Invalid agent selected",
        default_value=config.default_agent or "",
    )


def _update_llm_config(
    config: ForgeConfig,
    custom_model: str,
    base_url: str,
    api_key: str,
    agent: str,
    enable_confirmation_mode: bool,
    enable_memory_condensation: bool,
) -> None:
    """Update LLM configuration with new settings."""
    llm_config = config.get_llm_config()
    llm_config.model = custom_model
    llm_config.base_url = base_url
    llm_config.api_key = SecretStr(api_key)
    config.set_llm_config(llm_config)

    config.default_agent = agent
    config.security.confirmation_mode = enable_confirmation_mode
    config.enable_default_condenser = enable_memory_condensation

    _update_agent_condenser_config(config, llm_config, enable_memory_condensation)


def _update_agent_condenser_config(config: ForgeConfig, llm_config, enable_memory_condensation: bool) -> None:
    """Update agent condenser configuration."""
    agent_config = config.get_agent_config(config.default_agent)

    if enable_memory_condensation:
        agent_config.condenser = CondenserPipelineConfig(
            type="pipeline",
            condensers=[
                ConversationWindowCondenserConfig(type="conversation_window"),
                LLMSummarizingCondenserConfig(llm_config=llm_config, type="llm", keep_first=4, max_size=120),
            ],
        )
    else:
        agent_config.condenser = ConversationWindowCondenserConfig(type="conversation_window")

    config.set_agent_config(agent_config)


async def _save_settings_to_store(
    settings_store: FileSettingsStore,
    custom_model: str,
    base_url: str,
    api_key: str,
    agent: str,
    enable_confirmation_mode: bool,
    enable_memory_condensation: bool,
) -> None:
    """Save settings to the settings store."""
    settings = await settings_store.load() or Settings()
    settings.llm_model = custom_model
    settings.llm_api_key = SecretStr(api_key)
    settings.llm_base_url = base_url
    settings.agent = agent
    settings.confirmation_mode = enable_confirmation_mode
    settings.enable_default_condenser = enable_memory_condensation
    await settings_store.store(settings)


async def modify_llm_settings_advanced(config: ForgeConfig, settings_store: FileSettingsStore) -> None:
    """Modify advanced LLM settings (custom model, base URL, agent, features).
    
    Interactive wizard for advanced configuration options.
    
    Args:
        config: Forge configuration to modify
        settings_store: Settings storage backend

    """
    session = PromptSession(key_bindings=kb_cancel(), style=get_cli_style())
    llm_config = config.get_llm_config()

    try:
        custom_model, base_url, api_key, agent, enable_confirmation_mode, enable_memory_condensation = (
            await _collect_llm_settings_input(session, config, llm_config)
        )
    except (UserCancelledError, KeyboardInterrupt, EOFError):
        return

    save_settings = save_settings_confirmation(config)
    if not save_settings:
        return

    _update_llm_config(
        config,
        custom_model,
        base_url,
        api_key,
        agent,
        enable_confirmation_mode,
        enable_memory_condensation,
    )
    await _save_settings_to_store(
        settings_store,
        custom_model,
        base_url,
        api_key,
        agent,
        enable_confirmation_mode,
        enable_memory_condensation,
    )


def _display_search_api_info(config: ForgeConfig) -> None:
    """Display information about search API configuration (DEPRECATED)."""
    current_value = "********" if config.search_api_key else "Not Set"
    print_formatted_text("")
    print_formatted_text(HTML(f"<grey>Current Tavily Search API key: {current_value}</grey>"))
    print_formatted_text("")
async def _get_new_search_api_key(
    session: PromptSession,
    config: ForgeConfig,
    current_key: str,
) -> str:
    """Prompt user for a new search API key."""
    return await session.prompt_async(
        HTML("Enter Tavily Search API key (leave blank to cancel): "),
        default=current_key,
    )


async def _save_search_api_key(config: ForgeConfig, settings_store: FileSettingsStore, search_api_key: str) -> None:
    """Save search API key to config and settings store."""
    config.search_api_key = SecretStr(search_api_key) if search_api_key else None
    settings = await settings_store.load() or Settings()
    settings.search_api_key = SecretStr(search_api_key) if search_api_key else None
    await settings_store.store(settings)


async def modify_search_api_settings(config: ForgeConfig, settings_store: FileSettingsStore) -> None:
    """Modify search API settings."""
    session = PromptSession(key_bindings=kb_cancel(), style=get_cli_style())

    try:
        _display_search_api_info(config)
        current_key = config.search_api_key.get_secret_value() if config.search_api_key else ""
        action = cli_confirm(
            config,
            "\nHow would you like to update the Tavily Search API key?",
            ["Set new key", "Remove key", "Keep current key"],
        )

        if action == 2:
            return

        if action == 0:
            search_api_key = await _get_new_search_api_key(session, config, current_key)
            if search_api_key is None or not search_api_key.strip():
                return
            if not save_settings_confirmation(config):
                return
            await _save_search_api_key(config, settings_store, search_api_key.strip())
            return

        if action == 1:
            if cli_confirm(config, "\nRemove the Tavily Search API key?", ["Yes", "No"]) != 0:
                return
            await _save_search_api_key(config, settings_store, "")
            return
    except (UserCancelledError, KeyboardInterrupt, EOFError):
        return
