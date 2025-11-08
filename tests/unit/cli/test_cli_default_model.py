from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from forge.cli.settings import modify_llm_settings_basic
from forge.cli.utils import VERIFIED_ANTHROPIC_MODELS


@pytest.mark.asyncio
@patch("forge.cli.settings.get_supported_llm_models")
@patch("forge.cli.settings.organize_models_and_providers")
@patch("forge.cli.settings.PromptSession")
@patch("forge.cli.settings.cli_confirm")
@patch("forge.cli.settings.print_formatted_text")
async def test_anthropic_default_model_is_best_verified(
    mock_print, mock_confirm, mock_session, mock_organize, mock_get_models
):
    """Test that the default model for anthropic is the best verified model."""
    mock_get_models.return_value = ["anthropic/claude-sonnet-4-20250514", "anthropic/claude-2"]
    mock_organize.return_value = {"anthropic": {"models": ["claude-sonnet-4-20250514", "claude-2"], "separator": "/"}}
    session_instance = MagicMock()
    session_instance.prompt_async = AsyncMock(side_effect=KeyboardInterrupt())
    mock_session.return_value = session_instance
    app_config = MagicMock()
    llm_config = MagicMock()
    llm_config.model = "anthropic/claude-sonnet-4-20250514"
    app_config.get_llm_config.return_value = llm_config
    settings_store = AsyncMock()
    mock_confirm.side_effect = [0, 0, 0]
    try:
        await modify_llm_settings_basic(app_config, settings_store)
    except KeyboardInterrupt:
        pass
    best_verified_model = VERIFIED_ANTHROPIC_MODELS[0]
    default_model_displayed = False
    for call in mock_print.call_args_list:
        args, _ = call
        if (
            args
            and hasattr(args[0], "value")
            and (f"Default model: </grey><green>{best_verified_model}</green>" in args[0].value)
        ):
            default_model_displayed = True
            break
    assert default_model_displayed, f"Default model displayed was not {best_verified_model}"
