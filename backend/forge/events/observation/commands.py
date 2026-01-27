"""Observations produced by command execution."""

from __future__ import annotations

import json
import re
import traceback
from dataclasses import dataclass, field
from typing import Any, Self, ClassVar

from pydantic import BaseModel, Field, field_validator

from forge.core.logger import forge_logger as logger
from forge.core.schemas import ObservationType
from forge.events.observation.observation import Observation

CMD_OUTPUT_PS1_BEGIN = "\n###PS1JSON###\n"
CMD_OUTPUT_PS1_END = "\n###PS1END###"
CMD_OUTPUT_METADATA_PS1_REGEX = re.compile(
    f"^{CMD_OUTPUT_PS1_BEGIN.strip()}(.*?){CMD_OUTPUT_PS1_END.strip()}",
    re.DOTALL | re.MULTILINE,
)
MAX_CMD_OUTPUT_SIZE: int = 30000


class CmdOutputMetadata(BaseModel):
    """Additional metadata captured from PS1."""

    exit_code: int = Field(
        default=-1,
        description="Command exit code (-1 if unknown)"
    )
    pid: int = Field(
        default=-1,
        ge=-1,
        description="Process ID (-1 if unknown)"
    )
    username: str | None = Field(
        default=None,
        description="Username who executed the command"
    )
    hostname: str | None = Field(
        default=None,
        description="Hostname where the command was executed"
    )
    working_dir: str | None = Field(
        default=None,
        description="Working directory where the command was executed"
    )
    py_interpreter_path: str | None = Field(
        default=None,
        description="Path to the Python interpreter (if available)"
    )
    prefix: str = Field(
        default="",
        description="Prefix text to prepend to command output"
    )
    suffix: str = Field(
        default="",
        description="Suffix text to append to command output"
    )

    @field_validator("username", "hostname", "working_dir", "py_interpreter_path")
    @classmethod
    def validate_optional_strings(cls, v: str | None) -> str | None:
        """Validate optional string fields are non-empty if provided."""
        if v is not None:
            from forge.core.security.type_safety import validate_non_empty_string
            return validate_non_empty_string(v, name="field")
        return v

    @classmethod
    def to_ps1_prompt(cls) -> str:
        """Convert the required metadata into a PS1 prompt."""
        prompt = CMD_OUTPUT_PS1_BEGIN
        json_str = json.dumps(
            {
                "pid": "$!",
                "exit_code": "$?",
                "username": "\\u",
                "hostname": "\\h",
                "working_dir": "$(pwd)",
                "py_interpreter_path": '$(which python 2>/dev/null || echo "")',
            },
            indent=2,
        )
        prompt += json_str.replace('"', '\\"')
        prompt += CMD_OUTPUT_PS1_END + "\n"
        return prompt

    @classmethod
    def matches_ps1_metadata(cls, string: str) -> list[re.Match[str]]:
        """Find all PS1 metadata blocks in command output.

        Args:
            string: Command output string to search

        Returns:
            List of regex matches for PS1 metadata blocks

        """
        matches = []
        for match in CMD_OUTPUT_METADATA_PS1_REGEX.finditer(string):
            try:
                json.loads(match.group(1).strip())
                matches.append(match)
            except json.JSONDecodeError:
                logger.warning(
                    f"Failed to parse PS1 metadata: {match.group(1)}. Skipping.{traceback.format_exc()}"
                )
                continue
        return matches

    @classmethod
    def from_ps1_match(cls, match: re.Match[str]) -> Self:
        """Extract the required metadata from a PS1 prompt."""
        metadata = json.loads(match.group(1))
        processed = metadata.copy()
        if "pid" in metadata:
            try:
                processed["pid"] = int(float(str(metadata["pid"])))
            except (ValueError, TypeError):
                processed["pid"] = -1
        if "exit_code" in metadata:
            try:
                processed["exit_code"] = int(float(str(metadata["exit_code"])))
            except (ValueError, TypeError):
                logger.warning(
                    "Failed to parse exit code: %s. Setting to -1.",
                    metadata["exit_code"],
                )
                processed["exit_code"] = -1
        return cls(**processed)


@dataclass
class CmdOutputObservation(Observation):
    """This data class represents the output of a command."""

    command: str
    metadata: CmdOutputMetadata = field(default_factory=CmdOutputMetadata)
    hidden: bool = False
    observation: ClassVar[str] = ObservationType.RUN

    def __init__(
        self,
        content: str,
        command: str,
        observation: str = ObservationType.RUN,
        metadata: dict[str, Any] | CmdOutputMetadata | None = None,
        hidden: bool = False,
        **kwargs: Any,
    ) -> None:
        """Initialize the observation, coercing metadata and truncating content if needed."""
        truncate = not hidden
        if truncate:
            content = self._maybe_truncate(content)
        super().__init__(content)
        self.command = command
        self.observation = observation
        self.hidden = hidden
        if isinstance(metadata, dict):
            self.metadata = CmdOutputMetadata(**metadata)
        else:
            self.metadata = metadata or CmdOutputMetadata()
        if "exit_code" in kwargs:
            self.metadata.exit_code = kwargs["exit_code"]
        if "command_id" in kwargs:
            self.metadata.pid = kwargs["command_id"]

    @staticmethod
    def _maybe_truncate(content: str, max_size: int = MAX_CMD_OUTPUT_SIZE) -> str:
        """Truncate the content if it's too large.

        This helps avoid storing unnecessarily large content in the event stream.

        Args:
            content: The content to truncate
            max_size: Maximum size before truncation. Defaults to MAX_CMD_OUTPUT_SIZE.

        Returns:
            Original content if not too large, or truncated content otherwise

        """
        if len(content) <= max_size:
            return content
        half = max_size // 2
        original_length = len(content)
        truncated = (
            content[:half]
            + "\n[... Observation truncated due to length ...]\n"
            + content[-half:]
        )
        logger.debug(
            "Truncated large command output: %s -> %s chars",
            original_length,
            len(truncated),
        )
        return truncated

    @property
    def command_id(self) -> int:
        """Get command process ID."""
        return self.metadata.pid

    @command_id.setter
    def command_id(self, value: int) -> None:
        """Set command process ID."""
        self.metadata.pid = value

    @property
    def exit_code(self) -> int:
        """Get command exit code."""
        return self.metadata.exit_code

    @exit_code.setter
    def exit_code(self, value: int) -> None:
        """Set command exit code."""
        self.metadata.exit_code = value

    @property
    def error(self) -> bool:
        """Check if command failed (non-zero exit code)."""
        return self.exit_code != 0

    @property
    def message(self) -> str:
        """Get formatted command completion message."""
        return f"Command `{self.command}` executed with exit code {self.exit_code}."

    @property
    def success(self) -> bool:
        """Check if command succeeded (zero exit code)."""
        return not self.error

    def __str__(self) -> str:
        """Return a readable summary including metadata and agent-facing text."""
        from forge.core.pydantic_compat import model_dump_with_options

        try:
            metadata_json = json.dumps(model_dump_with_options(self.metadata), indent=2)
        except Exception:
            metadata_json = repr(self.metadata)
        return f"**CmdOutputObservation (source={self.source}, exit code={
            self.exit_code
        }, metadata={metadata_json})**\n--BEGIN AGENT OBSERVATION--\n{
            self.to_agent_observation()
        }\n--END AGENT OBSERVATION--"

    def to_agent_observation(self) -> str:
        """Format observation for agent with metadata context.

        Returns:
            Formatted observation string with working directory and exit code info

        """
        ret = f"{self.metadata.prefix}{self.content}{self.metadata.suffix}"
        if self.metadata.working_dir:
            ret += f"\n[Current working directory: {self.metadata.working_dir}]"
        if self.metadata.py_interpreter_path:
            ret += f"\n[Python interpreter: {self.metadata.py_interpreter_path}]"
        if self.metadata.exit_code != -1:
            ret += f"\n[Command finished with exit code {self.metadata.exit_code}]"
        return ret
