from __future__ import annotations
import unittest
from unittest.mock import MagicMock, patch
from forge.core.config.llm_config import LLMConfig
from forge.core.config.forge_config import ForgeConfig
from forge.llm.llm_registry import LLMRegistry, RegistryEvent


class TestLLMRegistry(unittest.TestCase):

    def setUp(self):
        """Set up test environment before each test."""
        self.llm_config = LLMConfig(model="test-model")
        self.config = ForgeConfig(llms={"llm": self.llm_config}, default_agent="CodeActAgent")
        self.registry = LLMRegistry(config=self.config)

    def test_get_llm_creates_new_llm(self):
        """Test that get_llm creates a new LLM when service doesn't exist."""
        service_id = "test-service"
        with patch.object(self.registry, "_create_new_llm") as mock_create:
            mock_llm = MagicMock()
            mock_llm.config = self.llm_config
            mock_create.return_value = mock_llm
            llm = self.registry.get_llm(service_id, self.llm_config)
            self.assertEqual(llm, mock_llm)
            mock_create.assert_called_once_with(config=self.llm_config, service_id=service_id)

    def test_get_llm_returns_existing_llm(self):
        """Test that get_llm returns existing LLM when service already exists."""
        service_id = "test-service"
        with patch.object(self.registry, "_create_new_llm") as mock_create:
            mock_llm = MagicMock()
            mock_llm.config = self.llm_config
            mock_create.return_value = mock_llm
            llm1 = self.registry.get_llm(service_id, self.llm_config)
            self.registry.service_to_llm[service_id] = mock_llm
            llm2 = self.registry.get_llm(service_id, self.llm_config)
            self.assertEqual(llm1, llm2)
            self.assertEqual(llm1, mock_llm)
            mock_create.assert_called_once()

    def test_get_llm_with_different_config_raises_error(self):
        """Test that requesting same service ID with different config raises an error."""
        service_id = "test-service"
        different_config = LLMConfig(model="different-model")
        mock_llm = MagicMock()
        mock_llm.config = self.llm_config
        self.registry.service_to_llm[service_id] = mock_llm
        with self.assertRaises(ValueError) as context:
            self.registry.get_llm(service_id, different_config)
        self.assertIn("Requesting same service ID", str(context.exception))
        self.assertIn("with different config", str(context.exception))

    def test_get_llm_without_config_raises_error(self):
        """Test that requesting new LLM without config raises an error."""
        service_id = "test-service"
        with self.assertRaises(ValueError) as context:
            self.registry.get_llm(service_id, None)
        self.assertIn("Requesting new LLM without specifying LLM config", str(context.exception))

    def test_request_extraneous_completion(self):
        """Test that requesting an extraneous completion creates a new LLM if needed."""
        service_id = "extraneous-service"
        messages = [{"role": "user", "content": "Hello, world!"}]
        with patch.object(self.registry, "_create_new_llm") as mock_create:
            mock_llm = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "  Hello from the LLM!  "
            mock_llm.completion.return_value = mock_response
            mock_create.return_value = mock_llm

            def side_effect(*args, **kwargs):
                self.registry.service_to_llm[service_id] = mock_llm
                return mock_llm

            mock_create.side_effect = side_effect
            response = self.registry.request_extraneous_completion(
                service_id=service_id, llm_config=self.llm_config, messages=messages
            )
            self.assertEqual(response, "Hello from the LLM!")
            mock_create.assert_called_once_with(config=self.llm_config, service_id=service_id, with_listener=False)
            mock_llm.completion.assert_called_once_with(messages=messages)

    def test_get_active_llm(self):
        """Test that get_active_llm returns the active agent LLM."""
        active_llm = self.registry.get_active_llm()
        self.assertEqual(active_llm, self.registry.active_agent_llm)

    def test_subscribe_and_notify(self):
        """Test the subscription and notification system."""
        events_received = []

        def callback(event: RegistryEvent):
            events_received.append(event)

        self.registry.subscribe(callback)
        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0].llm, self.registry.active_agent_llm)
        self.assertEqual(events_received[0].service_id, self.registry.active_agent_llm.service_id)
        self.assertIsNotNone(self.registry.subscriber)
        with patch.object(self.registry, "subscriber") as mock_subscriber:
            mock_event = MagicMock()
            self.registry.notify(mock_event)
            mock_subscriber.assert_called_once_with(mock_event)

    def test_registry_has_unique_id(self):
        """Test that each registry instance has a unique ID."""
        registry2 = LLMRegistry(config=self.config)
        self.assertNotEqual(self.registry.registry_id, registry2.registry_id)
        self.assertTrue(len(self.registry.registry_id) > 0)
        self.assertTrue(len(registry2.registry_id) > 0)


if __name__ == "__main__":
    unittest.main()
