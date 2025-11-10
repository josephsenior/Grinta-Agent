"""Serialization helpers for converting observations to and from dictionaries."""

from __future__ import annotations

import copy
from typing import Any

from forge.events.event import RecallType
from forge.events.observation.agent import (
    AgentCondensationObservation,
    AgentStateChangedObservation,
    AgentThinkObservation,
    MicroagentKnowledge,
    RecallObservation,
)
from forge.events.observation.browse import BrowserOutputObservation
from forge.events.observation.commands import (
    CmdOutputMetadata,
    CmdOutputObservation,
    IPythonRunCellObservation,
)
from forge.events.observation.delegate import AgentDelegateObservation
from forge.events.observation.empty import NullObservation
from forge.events.observation.error import ErrorObservation
from forge.events.observation.file_download import FileDownloadObservation
from forge.events.observation.files import (
    FileEditObservation,
    FileReadObservation,
    FileWriteObservation,
)
from forge.events.observation.mcp import MCPObservation
from forge.events.observation.observation import Observation
from forge.events.observation.reject import UserRejectObservation
from forge.events.observation.success import SuccessObservation
from forge.events.observation.task_tracking import TaskTrackingObservation

observations = (
    NullObservation,
    CmdOutputObservation,
    IPythonRunCellObservation,
    BrowserOutputObservation,
    FileReadObservation,
    FileWriteObservation,
    FileEditObservation,
    AgentDelegateObservation,
    SuccessObservation,
    ErrorObservation,
    AgentStateChangedObservation,
    UserRejectObservation,
    AgentCondensationObservation,
    AgentThinkObservation,
    RecallObservation,
    MCPObservation,
    FileDownloadObservation,
    TaskTrackingObservation,
)
OBSERVATION_TYPE_TO_CLASS = {observation_class.observation: observation_class for observation_class in observations}


def _update_cmd_output_metadata(
    metadata: dict[str, Any] | CmdOutputMetadata | None,
    **kwargs: Any,
) -> dict[str, Any] | CmdOutputMetadata:
    """Update the metadata of a CmdOutputObservation.

    If metadata is None, create a new CmdOutputMetadata instance.
    If metadata is a dict, update the dict.
    If metadata is a CmdOutputMetadata instance, update the instance.
    """
    if metadata is None:
        return CmdOutputMetadata(**kwargs)
    if isinstance(metadata, dict):
        metadata.update(**kwargs)
    elif isinstance(metadata, CmdOutputMetadata):
        for key, value in kwargs.items():
            setattr(metadata, key, value)
    return metadata


def handle_observation_deprecated_extras(extras: dict) -> dict:
    """Handle deprecated extras fields in observation dictionaries.
    
    Migrates legacy field names (exit_code, command_id) to new metadata structure
    and removes obsolete fields.
    
    Args:
        extras: Extras dictionary from observation
        
    Returns:
        Updated extras dictionary with deprecated fields migrated

    """
    if "exit_code" in extras:
        extras["metadata"] = _update_cmd_output_metadata(extras.get("metadata"), exit_code=extras.pop("exit_code"))
    if "command_id" in extras:
        extras["metadata"] = _update_cmd_output_metadata(extras.get("metadata"), pid=extras.pop("command_id"))
    if "formatted_output_and_error" in extras:
        extras.pop("formatted_output_and_error")
    return extras


def _validate_observation_dict(observation: dict) -> None:
    """Validate that observation dict has required keys."""
    if "observation" not in observation:
        msg = f"'observation' key is not found in observation={observation!r}"
        raise KeyError(msg)


def _get_observation_class(observation_type: str):
    """Get observation class from observation type."""
    observation_class = OBSERVATION_TYPE_TO_CLASS.get(observation_type)
    if observation_class is None:
        msg = f"'observation['observation']={
            observation_type!r}' is not defined. Available observations: {
            OBSERVATION_TYPE_TO_CLASS.keys()}"
        raise KeyError(
            msg,
        )
    return observation_class


def _extract_observation_data(observation: dict) -> tuple[str, dict]:
    """Extract content and extras from observation dict."""
    observation.pop("observation")
    observation.pop("message", None)
    content = observation.pop("content", "")
    extras = copy.deepcopy(observation.pop("extras", {}))
    extras = handle_observation_deprecated_extras(extras)
    # Remaining keys (e.g., command, metadata) should be treated as extras/kwargs
    if observation:
        extras.update(observation)
    return content, extras


def _process_cmd_output_metadata(extras: dict) -> None:
    """Process CmdOutputObservation metadata."""
    if "metadata" in extras and isinstance(extras["metadata"], dict):
        extras["metadata"] = CmdOutputMetadata(**extras["metadata"])
    elif "metadata" not in extras or not isinstance(extras["metadata"], CmdOutputMetadata):
        extras["metadata"] = CmdOutputMetadata()


def _process_recall_observation_data(extras: dict) -> None:
    """Process RecallObservation specific data."""
    if "recall_type" in extras:
        extras["recall_type"] = RecallType(extras["recall_type"])
    if "microagent_knowledge" in extras and isinstance(extras["microagent_knowledge"], list):
        extras["microagent_knowledge"] = [
            MicroagentKnowledge(**item) if isinstance(item, dict) else item for item in extras["microagent_knowledge"]
        ]


def observation_from_dict(observation: dict) -> Observation:
    """Deserialize observation from dictionary representation.
    
    Converts dictionary to Observation instance, handling special cases for
    CmdOutputObservation and RecallObservation types.
    
    Args:
        observation: Dictionary with observation type and data
        
    Returns:
        Deserialized Observation instance
        
    Raises:
        KeyError: If observation dict is invalid

    """
    observation = observation.copy()
    _validate_observation_dict(observation)
    observation_class = _get_observation_class(observation["observation"])
    content, extras = _extract_observation_data(observation)

    if observation_class is CmdOutputObservation:
        _process_cmd_output_metadata(extras)
    if observation_class is RecallObservation:
        _process_recall_observation_data(extras)

    obs = observation_class(content=content, **extras)
    assert isinstance(obs, Observation)
    return obs
