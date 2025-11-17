"""JSON serialization/deserialization helpers with Forge-specific encoding."""

import json
from datetime import datetime
from typing import Any

from json_repair import repair_json
from litellm.types.utils import ModelResponse

from forge.core.exceptions import LLMResponseError
from forge.core.pydantic_compat import model_dump_with_options
from forge.events.event import Event
from forge.events.observation import CmdOutputMetadata
from forge.events.serialization import event_to_dict
from forge.llm.metrics import Metrics
from pydantic import BaseModel


class ForgeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime and event objects."""

    def default(self, obj):
        """Serialize Forge-specific objects when dumping JSON."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Event):
            return event_to_dict(obj)
        if isinstance(obj, Metrics):
            return obj.get()
        if isinstance(obj, ModelResponse):
            return model_dump_with_options(obj)
        if isinstance(obj, CmdOutputMetadata):
            return model_dump_with_options(obj)
        return super().default(obj)


_json_encoder = ForgeJSONEncoder()


def dumps(obj, **kwargs):
    """Serialize an object to str format."""
    if not kwargs:
        return _json_encoder.encode(obj)
    encoder_kwargs = kwargs.copy()
    if "cls" not in encoder_kwargs:
        encoder_kwargs["cls"] = ForgeJSONEncoder
    return json.dumps(obj, **encoder_kwargs)


def print_json(obj, *, pretty: bool = False) -> None:
    """Print JSON using this module's encoder.

    Note: callers should prefer `forge.core.io.print_json_stdout` when
    emitting to stdout; this helper is provided for internal callers that use
    this module.
    """
    if pretty:
        pass
    else:
        pass


def loads(json_str, **kwargs):
    """Create a JSON object from str."""
    try:
        return json.loads(json_str, **kwargs)
    except json.JSONDecodeError:
        pass
    depth = 0
    start = -1
    for i, char in enumerate(json_str):
        if char == "{":
            if depth == 0:
                start = i
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0 and start != -1:
                response = json_str[start : i + 1]
                try:
                    json_str = repair_json(response)
                    return json.loads(json_str, **kwargs)
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    msg = "Invalid JSON in response. Please make sure the response is a valid JSON object."
                    raise LLMResponseError(
                        msg,
                    ) from e
    msg = "No valid JSON object found in response."
    raise LLMResponseError(msg)
