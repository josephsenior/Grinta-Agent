import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from forge.cli.main import run_setup_flow
from forge.core.config import ForgeConfig
from forge.storage.settings.file_settings_store import FileSettingsStore


class TestCLISetupFlow(unittest.TestCase):
    """Test the CLI setup flow."""

    @patch("forge.cli.settings.modify_llm_settings_basic")
    @patch("forge.cli.main.print_formatted_text")
    async def test_run_setup_flow(self, mock_print, mock_modify_settings):
        """Test that the setup flow calls the modify_llm_settings_basic function."""
        config = MagicMock(spec=ForgeConfig)
        settings_store = MagicMock(spec=FileSettingsStore)
        mock_modify_settings.return_value = None
        settings = MagicMock()
        settings_store.load = AsyncMock(return_value=settings)
        result = await run_setup_flow(config, settings_store)
        mock_modify_settings.assert_called_once_with(config, settings_store)
        self.assertGreaterEqual(mock_print.call_count, 2)
        self.assertTrue(result)

    @patch("forge.cli.main.print_formatted_text")
    @patch("forge.cli.main.run_setup_flow")
    @patch("forge.cli.main.FileSettingsStore.get_instance")
    @patch("forge.cli.main.setup_config_from_args")
    @patch("forge.cli.main.parse_arguments")
    async def test_main_calls_setup_flow_when_no_settings(
        self, mock_parse_args, mock_setup_config, mock_get_instance, mock_run_setup_flow, mock_print
    ):
        """Test that main calls run_setup_flow when no settings are found and exits."""
        mock_args = MagicMock()
        mock_config = MagicMock(spec=ForgeConfig)
        mock_settings_store = AsyncMock(spec=FileSettingsStore)
        mock_settings_store.load = AsyncMock(return_value=None)
        mock_parse_args.return_value = mock_args
        mock_setup_config.return_value = mock_config
        mock_get_instance.return_value = mock_settings_store
        mock_run_setup_flow.return_value = True
        from forge.cli.main import main

        loop = asyncio.get_event_loop()
        await main(loop)
        mock_run_setup_flow.assert_called_once_with(mock_config, mock_settings_store)
        self.assertEqual(mock_settings_store.load.call_count, 1)
        self.assertGreaterEqual(mock_print.call_count, 2)


def run_async_test(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


if __name__ == "__main__":
    unittest.main()
