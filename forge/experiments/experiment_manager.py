"""Experiment management utilities for applying per-conversation config overrides."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from pydantic import BaseModel

from forge.core.logger import forge_logger as logger
from forge.server.shared import file_store
from forge.storage.locations import get_experiment_config_filename
from forge.utils.import_utils import get_impl

if TYPE_CHECKING:
    from forge.core.config.forge_config import ForgeConfig
    from forge.server.session.conversation_init_data import ConversationInitData


class ExperimentConfig(BaseModel):
    """Model for optional experiment configuration overrides."""

    config: dict[str, str] | None = None


def load_experiment_config(conversation_id: str) -> ExperimentConfig | None:
    """Load experiment configuration JSON for a conversation if available."""
    try:
        file_path = get_experiment_config_filename(conversation_id)
        exp_config = file_store.read(file_path)
        return ExperimentConfig.model_validate_json(exp_config)
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.warning("Failed to load experiment config: %s", e)
    return None


class ExperimentManager:
    """Default no-op experiment manager that leaves config untouched."""

    @staticmethod
    def run_conversation_variant_test(
        user_id: str,
        conversation_id: str,
        conversation_settings: ConversationInitData,
    ) -> ConversationInitData:
        """Return conversation settings unchanged (variant testing not implemented)."""
        return conversation_settings

    @staticmethod
    def run_config_variant_test(
        user_id: str, conversation_id: str, config: ForgeConfig
    ) -> ForgeConfig:
        """Apply experiment config overrides to agent config if present."""
        exp_config = load_experiment_config(conversation_id)
        if exp_config and exp_config.config:
            agent_cfg = config.get_agent_config(config.default_agent)
            try:
                for attr, value in exp_config.config.items():
                    if hasattr(agent_cfg, attr):
                        logger.info(
                            "Set attrib %s to %s for %s", attr, value, conversation_id
                        )
                        setattr(agent_cfg, attr, value)
            except Exception as e:
                logger.warning("Error processing exp config: %s", e)
        return config


experiment_manager_cls = os.environ.get(
    "FORGE_EXPERIMENT_MANAGER_CLS",
    "forge.experiments.experiment_manager.ExperimentManager",
)
ExperimentManagerImpl = get_impl(ExperimentManager, experiment_manager_cls)
