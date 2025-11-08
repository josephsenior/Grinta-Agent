"""Observations produced by command execution and IPython interactions."""

from __future__ import annotations

import json
import re
import traceback
from dataclasses import dataclass, field
from typing import Any, Self

from pydantic import BaseModel

from forge.core.logger import forge_logger as logger
from forge.core.schema import ObservationType
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

    exit_code: int = -1
    pid: int = -1
    username: str | None = None
    hostname: str | None = None
    working_dir: str | None = None
    py_interpreter_path: str | None = None
    prefix: str = ""
    suffix: str = ""

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
                logger.warning(f"Failed to parse PS1 metadata: {match.group(1)}. Skipping.{traceback.format_exc()}")
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
                logger.warning("Failed to parse exit code: %s. Setting to -1.", metadata["exit_code"])
                processed["exit_code"] = -1
        return cls(**processed)


@dataclass
class CmdOutputObservation(Observation):
    """This data class represents the output of a command."""

    command: str
    observation: str = ObservationType.RUN
    metadata: CmdOutputMetadata = field(default_factory=CmdOutputMetadata)
    hidden: bool = False

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
        truncated = content[:half] + "\n[... Observation truncated due to length ...]\n" + content[-half:]
        logger.debug("Truncated large command output: %s -> %s chars", original_length, len(truncated))
        return truncated

    @property
    def command_id(self) -> int:
        """Get command process ID."""
        return self.metadata.pid

    @property
    def exit_code(self) -> int:
        """Get command exit code."""
        return self.metadata.exit_code

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
        return f"**CmdOutputObservation (source={
            self.source}, exit code={
            self.exit_code}, metadata={metadata_json})**\n--BEGIN AGENT OBSERVATION--\n{
            self.to_agent_observation()}\n--END AGENT OBSERVATION--"

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


@dataclass
class IPythonRunCellObservation(Observation):
    """This data class represents the output of a IPythonRunCellAction."""

    code: str
    observation: str = ObservationType.RUN_IPYTHON
    image_urls: list[str] | None = None

    @property
    def error(self) -> bool:
        """Check if IPython execution had error (always False)."""
        return False

    @property
    def message(self) -> str:
        """Get IPython execution completion message."""
        return "Code executed in IPython cell."

    @property
    def success(self) -> bool:
        """Check if IPython execution succeeded (always True)."""
        return True

    def __str__(self) -> str:
        """Return a readable summary including output content and images."""
        result = f"**IPythonRunCellObservation**\n{self.content}"
        if self.image_urls:
            result += f"\nImages: {len(self.image_urls)}"
        return result

    __test__ = False
