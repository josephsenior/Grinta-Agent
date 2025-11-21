"""Additional coverage for command observation utilities."""

from __future__ import annotations

import json
from textwrap import dedent

import pytest

from forge.events.observation.commands import (
    CmdOutputMetadata,
    CmdOutputObservation,
    MAX_CMD_OUTPUT_SIZE,
)


def test_cmd_output_metadata_to_ps1_prompt_is_well_formed() -> None:
    prompt = CmdOutputMetadata.to_ps1_prompt()
    assert prompt.startswith("\n###PS1JSON###")
    assert prompt.strip().endswith("###PS1END###")
    # Ensure JSON payload in middle parses once escapes removed
    payload = prompt.split("###PS1JSON###")[1].split("###PS1END###")[0]
    payload = payload.replace('\\"', '"')
    json.loads(payload)


def test_cmd_output_metadata_matches_and_parses() -> None:
    metadata_block = dedent(
        """
        ###PS1JSON###
        {"pid": "123", "exit_code": "0", "username": "user", "hostname": "host"}
        ###PS1END###
        """
    )
    matches = CmdOutputMetadata.matches_ps1_metadata(metadata_block)
    assert len(matches) == 1
    metadata = CmdOutputMetadata.from_ps1_match(matches[0])
    assert metadata.pid == 123
    assert metadata.exit_code == 0
    assert metadata.username == "user"
    assert metadata.hostname == "host"


def test_cmd_output_observation_truncates_when_visible() -> None:
    huge_content = "a" * (MAX_CMD_OUTPUT_SIZE + 100)
    obs = CmdOutputObservation(content=huge_content, command="echo test", hidden=False)
    assert len(obs.content) < len(huge_content)
    assert "[... Observation truncated due to length ...]" in obs.content


def test_cmd_output_observation_preserves_content_when_hidden() -> None:
    huge_content = "b" * (MAX_CMD_OUTPUT_SIZE + 10)
    obs = CmdOutputObservation(content=huge_content, command="echo test", hidden=True)
    assert obs.content == huge_content


def test_cmd_output_observation_properties() -> None:
    obs = CmdOutputObservation(
        content="ok",
        command="ls",
        metadata={"exit_code": 2, "working_dir": "/tmp", "prefix": ">", "suffix": "<"},
        hidden=False,
    )
    assert obs.exit_code == 2
    assert obs.command_id == -1
    assert obs.error is True
    assert obs.success is False
    assert "Command `ls` executed with exit code 2." in obs.message
    agent_view = obs.to_agent_observation()
    assert agent_view.startswith(">")
    assert "[Current working directory: /tmp]" in agent_view
    assert agent_view.rstrip().endswith("exit code 2]")


def test_cmd_output_observation_str_includes_metadata_json() -> None:
    obs = CmdOutputObservation(
        content="output",
        command="cmd",
        metadata=CmdOutputMetadata(exit_code=0, prefix="[", suffix="]"),
    )
    repr_str = str(obs)
    assert "**CmdOutputObservation" in repr_str
    assert '"exit_code": 0' in repr_str
