"""Shared helper functions for loading and working with Forge config files."""

from __future__ import annotations

import os
import pathlib
import platform
import sys
from ast import literal_eval
from dataclasses import dataclass
from types import UnionType
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)
from uuid import uuid4

import toml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from forge.core import logger
from forge.core.config.arg_utils import get_headless_parser
from forge.core.config.llm_config import LLMConfig
from forge.core.config.agent_config import AgentConfig

# Condenser configs imported lazily to avoid circular dependencies
from forge.core.config.extended_config import ExtendedConfig
# from forge.core.config.kubernetes_config import KubernetesConfig
from forge.core.config.mcp_config import MCPConfig
from forge.core.config.forge_config import ForgeConfig
from forge.core.config.sandbox_config import SandboxConfig
from forge.core.config.security_config import SecurityConfig
from forge.storage import get_file_store
from forge.utils.import_utils import get_impl

if TYPE_CHECKING:
    import argparse
    from collections.abc import MutableMapping

    from forge.storage.files import FileStore
    from forge.core.config.condenser_config import CondenserConfig

JWT_SECRET = ".jwt_secret"
load_dotenv()


@dataclass
class _ConfigIssue:
    section: str
    reason: str
    detail: str


class ConfigLoadSummary:
    """Aggregate warnings encountered while loading configuration sections."""

    def __init__(self, toml_file: str) -> None:
        self._toml_file = toml_file
        self._issues: list[_ConfigIssue] = []

    def record(self, section: str, reason: str, detail: str) -> None:
        detail_str = (detail or "").strip()
        if len(detail_str) > 240:
            detail_str = f"{detail_str[:237]}..."
        self._issues.append(_ConfigIssue(section=section, reason=reason, detail=detail_str))

    def record_missing(self, section: str, detail: str) -> None:
        self.record(section, "missing", detail)

    def emit(self) -> None:
        if not self._issues:
            return
        grouped: dict[str, list[_ConfigIssue]] = {}
        for issue in self._issues:
            grouped.setdefault(issue.section, []).append(issue)
        lines: list[str] = []
        for section in sorted(grouped.keys()):
            reasons = "; ".join(
                f"{issue.reason}: {issue.detail}" if issue.detail else issue.reason
                for issue in grouped[section]
            )
            lines.append(f"[{section}] {reasons}")
        logger.FORGE_logger.warning(
            "Configuration sections skipped or partially applied while loading %s:\n%s",
            self._toml_file,
            "\n".join(lines),
        )


def _to_posix_workspace_path(path: str) -> str:
    """Convert an OS-specific absolute path to a POSIX-style path.

    On Windows, strip any drive letter and ensure the path starts with '/'.
    Backslashes are replaced with forward slashes. This is only used for logical
    rewrite / comparison operations & values exposed via config (not for direct
    filesystem calls).
    """
    if not path:
        return path
    p = path.replace("\\", "/")
    if len(p) >= 2 and p[1] == ":":
        p = p[2:]
    if not p.startswith("/"):
        p = f"/{p}"
    while "//" in p:
        p = p.replace("//", "/")
    return p.rstrip("/") if p != "/" else p


def _get_optional_type(union_type: UnionType | type | None) -> type | None:
    """Return the non-None type from a union.

    Args:
        union_type: The union type to extract the non-None type from.

    Returns:
        type | None: The non-None type if found, None otherwise.

    """
    if union_type is None:
        return None
    if get_origin(union_type) is UnionType:
        types = get_args(union_type)
        return next((t for t in types if t is not type(None)), None)
    return union_type if isinstance(union_type, type) else None


def _is_dict_or_list_type(field_type: Any) -> bool:
    """Check if field type is dict or list.

    Args:
        field_type: The field type to check.

    Returns:
        bool: True if the field type is dict or list, False otherwise.

    """
    origin = get_origin(field_type)
    return origin is dict or origin is list or field_type is dict or field_type is list


def _process_list_items(cast_value: list, field_type: Any) -> list:
    """Process list items if inner type is BaseModel.

    Args:
        cast_value: The list value to process.
        field_type: The field type containing the inner type information.

    Returns:
        list: The processed list with BaseModel instances if applicable.

    """
    inner_type = get_args(field_type)[0]
    if isinstance(inner_type, type) and issubclass(inner_type, BaseModel):
        return [
            inner_type(**item) if isinstance(item, dict) else item
            for item in cast_value
        ]
    return cast_value


def _cast_value_to_type(value: str, field_type: Any) -> Any:
    """Cast string value to appropriate type.

    Args:
        value: The string value to cast.
        field_type: The target field type.

    Returns:
        Any: The cast value.

    """
    # Handle Union types
    if get_origin(field_type) is UnionType:
        field_type = _get_optional_type(field_type)

    # Handle boolean values
    if field_type is bool:
        return value.lower() in {"true", "1"}

    # Handle dict and list types
    if _is_dict_or_list_type(field_type):
        cast_value = literal_eval(value)
        if get_origin(field_type) is list:
            cast_value = _process_list_items(cast_value, field_type)
        return cast_value

    # Handle SecretStr explicitly to avoid unintended casting behaviour
    from pydantic import SecretStr  # Local import to avoid circular deps during typing

    if isinstance(field_type, type) and issubclass(field_type, SecretStr):
        return SecretStr(value)

    # Handle other types
    return field_type(value) if field_type is not None else value


def _process_field_value(
    sub_config: BaseModel,
    field_name: str,
    field_type: Any,
    env_var_name: str,
    env_dict: dict,
) -> None:
    """Process and set field value from environment variable.

    Args:
        sub_config: The configuration model to update.
        field_name: The name of the field to set.
        field_type: The type of the field.
        env_var_name: The environment variable name.
        env_dict: The dictionary containing environment variables.

    """
    value = env_dict[env_var_name]
    if not value:
        return

    try:
        from pydantic import (
            SecretStr,
        )  # Local import to avoid circular dependencies during runtime

        if field_name.lower().endswith("api_key"):
            cast_value = SecretStr(value)
        else:
            cast_value = _cast_value_to_type(value, field_type)
        setattr(sub_config, field_name, cast_value)

        if field_name == "api_key":
            try:
                from forge.core.config.api_key_manager import api_key_manager

                if hasattr(sub_config, "model") and cast_value is not None:
                    api_key_manager.set_api_key(sub_config.model, cast_value)
                    api_key_manager.set_environment_variables(
                        sub_config.model, cast_value
                    )
            except Exception:
                # Avoid hard failure if API key manager encounters issues during config load
                logger.FORGE_logger.debug("Failed to sync API key manager")
    except (ValueError, TypeError):
        logger.FORGE_logger.error(
            "Error setting env var %s=<redacted>: check that the value is of the right type",
            env_var_name,
        )


def _set_attr_from_env(
    sub_config: BaseModel,
    env_dict: dict,
    prefix: str = "",
) -> None:
    """Set attributes of a config model based on environment variables.

    Args:
        sub_config: The configuration model to update.
        env_dict: The dictionary containing environment variables.
        prefix: The prefix for environment variable names.

    """
    for field_name, field_info in sub_config.__class__.model_fields.items():
        field_value = getattr(sub_config, field_name)
        field_type = field_info.annotation
        env_var_name = (prefix + field_name).upper()

        if isinstance(field_value, BaseModel):
            _set_attr_from_env(field_value, env_dict, prefix=f"{field_name}_")
        elif env_var_name in env_dict:
            _process_field_value(
                sub_config, field_name, field_type, env_var_name, env_dict
            )


def load_from_env(
    cfg: ForgeConfig, env_or_toml_dict: dict | MutableMapping[str, str]
) -> None:
    """Set config attributes from environment variables or TOML dictionary.

    Args:
        cfg: The Forge configuration object to update.
        env_or_toml_dict: Dictionary containing environment variables or TOML values.

    """
    # Work on a shallow copy so runtime mutations (e.g. from API key manager)
    # don't overwrite the values being loaded from the caller.
    env_dict = dict(env_or_toml_dict)

    # Apply configuration to main config and sub-configs
    _set_attr_from_env(cfg, env_dict)
    default_llm_config = cfg.get_llm_config()
    _set_attr_from_env(default_llm_config, env_dict, "LLM_")

    if "LLM_API_KEY" in env_dict:
        from forge.core.config.llm_config import LLMConfig, suppress_llm_env_export

        updated_data = default_llm_config.model_dump()
        # Ensure we don't use masked secret values from model_dump
        if isinstance(default_llm_config.api_key, SecretStr):
            updated_data["api_key"] = default_llm_config.api_key.get_secret_value()

        updated_data["api_key"] = env_dict["LLM_API_KEY"]
        with suppress_llm_env_export():
            new_config = LLMConfig.model_validate(updated_data)
        cfg.set_llm_config(new_config)
    else:
        cfg.set_llm_config(default_llm_config)
    _set_attr_from_env(cfg.get_agent_config(), env_dict, "AGENT_")


def _restore_environment(original_env: dict[str, str]) -> None:
    """Restore environment variables to their original state after config load side-effects."""
    current_keys = set(os.environ.keys())
    original_keys = set(original_env.keys())

    for added_key in current_keys - original_keys:
        os.environ.pop(added_key, None)

    for key in original_keys:
        os.environ[key] = original_env[key]


def _export_llm_api_keys(cfg: ForgeConfig) -> None:
    """Export LLM API keys to environment after all overrides are applied."""
    try:
        from forge.core.config.api_key_manager import api_key_manager

        for llm in cfg.llms.values():
            if llm.api_key:
                api_key_manager.set_api_key(llm.model, llm.api_key)
                api_key_manager.set_environment_variables(llm.model, llm.api_key)
    except Exception:
        logger.FORGE_logger.debug(
            "Failed to export LLM API keys after configuration load"
        )


def _process_core_section(
    core_config: dict, cfg: ForgeConfig, summary: ConfigLoadSummary | None = None
) -> None:
    """Process the [core] section of the TOML config."""
    try:
        cfg_type_hints = get_type_hints(cfg.__class__)
    except NameError:
        cfg_type_hints = getattr(cfg.__class__, "__annotations__", {})
    for key, value in core_config.items():
        if hasattr(cfg, key):
            if expected_type := cfg_type_hints.get(key, None):
                origin = get_origin(expected_type)
                args = get_args(expected_type)
                if (
                    origin is UnionType and SecretStr in args and isinstance(value, str)
                ) or (expected_type is SecretStr and isinstance(value, str)):
                    value = SecretStr(value)
            setattr(cfg, key, value)
        else:
            logger.FORGE_logger.warning(
                'Unknown config key "%s" in [core] section', key
            )


def _process_agent_section(
    toml_config: dict, cfg: ForgeConfig, summary: ConfigLoadSummary | None = None
) -> None:
    """Process the [agent] section of the TOML config."""
    if "agent" in toml_config:
        try:
            agent_instance = AgentConfig()
            agent_mapping = agent_instance.from_dict(toml_config["agent"])
            for agent_key, agent_conf in agent_mapping.items():
                cfg.set_agent_config(agent_conf, agent_key)
        except (TypeError, KeyError, ValidationError) as e:
            logger.FORGE_logger.warning(
                "Cannot parse [agent] config from toml, values have not been applied.\nError: %s",
                e,
            )
            if summary:
                summary.record("agent", "invalid", str(e))


def _process_llm_section(
    toml_config: dict, cfg: ForgeConfig, summary: ConfigLoadSummary | None = None
) -> None:
    """Process the [llm] section of the TOML config."""
    if "llm" in toml_config:
        from forge.core.config.llm_config import suppress_llm_env_export

        try:
            with suppress_llm_env_export():
                llm_instance = LLMConfig()
                llm_mapping = llm_instance.from_toml_section(toml_config["llm"])

            base_llm = llm_mapping.pop("llm", None)
            for llm_key, llm_conf in llm_mapping.items():
                cfg.set_llm_config(llm_conf, llm_key)
            if base_llm is not None:
                cfg.set_llm_config(base_llm, "llm")
        except (TypeError, KeyError, ValidationError) as e:
            logger.FORGE_logger.warning(
                "Cannot parse [llm] config from toml, values have not been applied.\nError: %s",
                e,
            )
            if summary:
                summary.record("llm", "invalid", str(e))


def _process_security_section(
    toml_config: dict, cfg: ForgeConfig, summary: ConfigLoadSummary | None = None
) -> None:
    """Process the [security] section of the TOML config."""
    if "security" in toml_config:
        try:
            security_mapping = SecurityConfig.from_toml_section(toml_config["security"])
            if "security" in security_mapping:
                cfg.security = security_mapping["security"]
        except (TypeError, KeyError, ValidationError) as e:
            logger.FORGE_logger.warning(
                "Cannot parse [security] config from toml, values have not been applied.\nError: %s",
                e,
            )
            if summary:
                summary.record("security", "invalid", str(e))
        except ValueError as exc:
            if summary:
                summary.record("security", "error", str(exc))
            msg = "Error in [security] section in config.toml"
            raise ValueError(msg) from exc


def _process_sandbox_section(
    toml_config: dict, cfg: ForgeConfig, summary: ConfigLoadSummary | None = None
) -> None:
    """Process the [sandbox] section of the TOML config."""
    if "sandbox" in toml_config:
        try:
            sandbox_mapping = SandboxConfig.from_toml_section(toml_config["sandbox"])
            if "sandbox" in sandbox_mapping:
                cfg.sandbox = sandbox_mapping["sandbox"]
        except (TypeError, KeyError, ValidationError) as e:
            logger.FORGE_logger.warning(
                "Cannot parse [sandbox] config from toml, values have not been applied.\nError: %s",
                e,
            )
            if summary:
                summary.record("sandbox", "invalid", str(e))
        except ValueError as e:
            if summary:
                summary.record("sandbox", "error", str(e))
            msg = "Error in [sandbox] section in config.toml"
            raise ValueError(msg) from e


def _process_mcp_section(
    toml_config: dict, cfg: ForgeConfig, summary: ConfigLoadSummary | None = None
) -> None:
    """Process the [mcp] section of the TOML config."""
    if "mcp" in toml_config:
        try:
            mcp_mapping = MCPConfig.from_toml_section(toml_config["mcp"])
            if "mcp" in mcp_mapping:
                cfg.mcp = mcp_mapping["mcp"]
        except (TypeError, KeyError, ValidationError) as e:
            logger.FORGE_logger.warning(
                "Cannot parse MCP config from toml, values have not been applied.\nError: %s",
                e,
            )
            if summary:
                summary.record("mcp", "invalid", str(e))
        except ValueError as err:
            if summary:
                summary.record("mcp", "error", str(err))
            msg = "Error in MCP sections in config.toml"
            raise ValueError(msg) from err


def _process_condenser_section(
    toml_config: dict, cfg: ForgeConfig, summary: ConfigLoadSummary | None = None
) -> None:
    """Process the [condenser] section of the TOML config."""
    if "condenser" in toml_config:
        try:
            from forge.core.config.condenser_config import (
                condenser_config_from_toml_section,
            )

            condenser_mapping = condenser_config_from_toml_section(
                toml_config["condenser"], cfg.llms
            )
            if "condenser" in condenser_mapping:
                default_agent_config = cfg.get_agent_config()
                default_agent_config.condenser_config = condenser_mapping["condenser"]
                logger.FORGE_logger.debug(
                    "Default condenser configuration loaded from config toml and assigned to default agent",
                )
        except (TypeError, KeyError, ValidationError) as e:
            logger.FORGE_logger.warning(
                "Cannot parse [condenser] config from toml, values have not been applied.\nError: %s",
                e,
            )
            if summary:
                summary.record("condenser", "invalid", str(e))
    elif cfg.enable_default_condenser:
        from forge.core.config.condenser_config import LLMSummarizingCondenserConfig

        default_agent_config = cfg.get_agent_config()
        default_condenser = LLMSummarizingCondenserConfig(
            llm_config=cfg.get_llm_config(), type="llm"
        )
        default_agent_config.condenser_config = default_condenser
        logger.FORGE_logger.debug(
            "Default LLM summarizing condenser assigned to default agent (no condenser in config)",
        )


def _process_extended_section(
    toml_config: dict, cfg: ForgeConfig, summary: ConfigLoadSummary | None = None
) -> None:
    """Process the [extended] section of the TOML config."""
    if "extended" in toml_config:
        try:
            cfg.extended = ExtendedConfig(toml_config["extended"])
        except (TypeError, KeyError, ValidationError) as e:
            logger.FORGE_logger.warning(
                "Cannot parse [extended] config from toml, values have not been applied.\nError: %s",
                e,
            )
            if summary:
                summary.record("extended", "invalid", str(e))


def _check_unknown_sections(toml_config: dict, toml_file: str) -> None:
    """Check for unknown sections in the TOML config."""
    known_sections = {
        "core",
        "extended",
        "agent",
        "llm",
        "security",
        "sandbox",
        "condenser",
        "mcp",
    }
    for key in toml_config:
        if key.lower() not in known_sections:
            logger.FORGE_logger.debug("Unknown section [%s] in %s", key, toml_file)


def load_from_toml(cfg: ForgeConfig, toml_file: str = "config.toml") -> None:
    """Load the config from the toml file. Supports both styles of config vars.

    Args:
        cfg: The ForgeConfig object to update attributes of.
        toml_file: The path to the toml file. Defaults to 'config.toml'.

    See Also:
    - config.template.toml for the full list of config options.

    """
    summary = ConfigLoadSummary(toml_file)
    try:
        try:
            with open(toml_file, encoding="utf-8") as toml_contents:
                toml_config = toml.load(toml_contents)
        except FileNotFoundError:
            return
        except toml.TomlDecodeError as e:
            logger.FORGE_logger.warning(
                "Cannot parse config from toml, toml values have not been applied.\nError: %s",
                e,
            )
            return
        if "core" not in toml_config:
            logger.FORGE_logger.warning(
                "No [core] section found in %s. Core settings will use defaults.",
                toml_file,
            )
            summary.record_missing("core", "section missing; defaults applied")
            core_config = {}
        else:
            core_config = toml_config["core"]
        _process_core_section(core_config, cfg, summary)
        _process_agent_section(toml_config, cfg, summary)
        _process_llm_section(toml_config, cfg, summary)
        _process_security_section(toml_config, cfg, summary)
        _process_sandbox_section(toml_config, cfg, summary)
        _process_mcp_section(toml_config, cfg, summary)
        _process_condenser_section(toml_config, cfg, summary)
        _process_extended_section(toml_config, cfg, summary)
        _check_unknown_sections(toml_config, toml_file)
    finally:
        summary.emit()


def get_or_create_jwt_secret(file_store: FileStore) -> str:
    """Get existing JWT secret or create a new one if not found.

    Args:
        file_store: File store to read/write JWT secret

    Returns:
        JWT secret string (hex UUID)

    """
    try:
        return file_store.read(JWT_SECRET)
    except FileNotFoundError:
        new_secret = uuid4().hex
        file_store.write(JWT_SECRET, new_secret)
        return new_secret


def finalize_config(cfg: ForgeConfig) -> None:
    """More tweaks to the config after it's been loaded."""
    _configure_llm_logging(cfg)
    _ensure_cache_directory(cfg)
    _configure_jwt_secret(cfg)


def _configure_llm_logging(cfg: ForgeConfig) -> None:
    """Configure LLM logging paths."""
    for llm in cfg.llms.values():
        llm.log_completions_folder = os.path.abspath(llm.log_completions_folder)


def _ensure_cache_directory(cfg: ForgeConfig) -> None:
    """Ensure cache directory exists."""
    if cfg.cache_dir:
        pathlib.Path(cfg.cache_dir).mkdir(parents=True, exist_ok=True)


def _configure_jwt_secret(cfg: ForgeConfig) -> None:
    """Configure JWT secret if not set."""
    if not cfg.jwt_secret:
        cfg.jwt_secret = SecretStr(
            get_or_create_jwt_secret(
                get_file_store(cfg.file_store, cfg.file_store_path)
            )
        )


def get_agent_config_arg(
    agent_config_arg: str, toml_file: str = "config.toml"
) -> AgentConfig | None:
    """Get a group of agent settings from the config file.

    A group in config.toml can look like this:

    ```
    [agent.default]
    enable_prompt_extensions = false
    ```

    The user-defined group name, like "default", is the argument to this function. The function will load the AgentConfig object
    with the settings of this group, from the config file, and set it as the AgentConfig object for the app.

    Note that the group must be under "agent" group, or in other words, the group name must start with "agent.".

    Args:
        agent_config_arg: The group of agent settings to get from the config.toml file.
        toml_file: Path to the configuration file to read from. Defaults to 'config.toml'.

    Returns:
        AgentConfig: The AgentConfig object with the settings from the config file.

    """
    agent_config_arg = agent_config_arg.strip("[]")
    agent_config_arg = agent_config_arg.removeprefix("agent.")
    logger.FORGE_logger.debug("Loading agent config from %s", agent_config_arg)
    try:
        with open(toml_file, encoding="utf-8") as toml_contents:
            toml_config = toml.load(toml_contents)
    except FileNotFoundError as e:
        logger.FORGE_logger.error("Config file not found: %s", e)
        return None
    except toml.TomlDecodeError as e:
        logger.FORGE_logger.error(
            "Cannot parse agent group from %s. Exception: %s", agent_config_arg, e
        )
        return None
    if "agent" in toml_config and agent_config_arg in toml_config["agent"]:
        return AgentConfig(**toml_config["agent"][agent_config_arg])
    logger.FORGE_logger.debug("Loading from toml failed for %s", agent_config_arg)
    return None


def get_llm_config_arg(
    llm_config_arg: str, toml_file: str = "config.toml"
) -> LLMConfig | None:
    """Get a group of llm settings from the config file.

    A group in config.toml can look like this:

    ```
    [llm.gpt-3.5-for-eval]
    model = 'gpt-3.5-turbo'
    api_key = '...'
    temperature = 0.5
    num_retries = 8
    ...
    ```

    The user-defined group name, like "gpt-3.5-for-eval", is the argument to this function. The function will load the LLMConfig object
    with the settings of this group, from the config file, and set it as the LLMConfig object for the app.

    Note that the group must be under "llm" group, or in other words, the group name must start with "llm.".

    Args:
        llm_config_arg: The group of llm settings to get from the config.toml file.
        toml_file: Path to the configuration file to read from. Defaults to 'config.toml'.

    Returns:
        LLMConfig: The LLMConfig object with the settings from the config file.

    """
    llm_config_arg = llm_config_arg.strip("[]")
    llm_config_arg = llm_config_arg.removeprefix("llm.")
    logger.FORGE_logger.debug(
        'Loading llm config "%s" from %s', llm_config_arg, toml_file
    )
    if not os.path.exists(toml_file):
        logger.FORGE_logger.debug("Config file not found: %s", toml_file)
        return None
    try:
        with open(toml_file, encoding="utf-8") as toml_contents:
            toml_config = toml.load(toml_contents)
    except FileNotFoundError as e:
        logger.FORGE_logger.error("Config file not found: %s", e)
        return None
    except toml.TomlDecodeError as e:
        logger.FORGE_logger.error(
            "Cannot parse llm group from %s. Exception: %s", llm_config_arg, e
        )
        return None
    if "llm" in toml_config and llm_config_arg in toml_config["llm"]:
        return LLMConfig(**toml_config["llm"][llm_config_arg])
    logger.FORGE_logger.debug(
        'LLM config "%s" not found in %s', llm_config_arg, toml_file
    )
    return None


def _load_toml_config(toml_file: str) -> dict | None:
    """Load and parse TOML configuration file."""
    try:
        with open(toml_file, encoding="utf-8") as toml_contents:
            return toml.load(toml_contents)
    except FileNotFoundError as e:
        logger.FORGE_logger.error("Config file not found: %s. Error: %s", toml_file, e)
        return None
    except toml.TomlDecodeError as e:
        logger.FORGE_logger.error(
            "Cannot parse config file %s. Exception: %s", toml_file, e
        )
        return None


def _validate_condenser_section(
    toml_config: dict, condenser_config_arg: str, toml_file: str
) -> dict | None:
    """Validate that condenser section exists and return condenser data."""
    if (
        "condenser" not in toml_config
        or condenser_config_arg not in toml_config["condenser"]
    ):
        logger.FORGE_logger.error(
            "Condenser config section [condenser.%s] not found in %s",
            condenser_config_arg,
            toml_file,
        )
        return None
    return toml_config["condenser"][condenser_config_arg].copy()


def _process_llm_condenser(
    condenser_data: dict, condenser_config_arg: str, toml_file: str
) -> dict | None:
    """Process LLM-type condenser configuration."""
    llm_config_name = condenser_data["llm_config"]
    logger.FORGE_logger.debug(
        "Condenser [%s] requires LLM config [%s]. Loading it...",
        condenser_config_arg,
        llm_config_name,
    )
    if referenced_llm_config := get_llm_config_arg(
        llm_config_name, toml_file=toml_file
    ):
        condenser_data["llm_config"] = referenced_llm_config
        return condenser_data
    logger.FORGE_logger.error(
        "Failed to load required LLM config '%s' for condenser '%s'.",
        llm_config_name,
        condenser_config_arg,
    )
    return None


def _normalize_condenser_config_arg(condenser_config_arg: str) -> str:
    """Normalize condenser config argument by removing brackets and prefix."""
    return condenser_config_arg.strip("[]").removeprefix("condenser.")


def _validate_condenser_type(
    condenser_data: dict, condenser_config_arg: str, toml_file: str
) -> str | None:
    """Validate that condenser type is specified."""
    condenser_type = condenser_data.get("type")
    if not condenser_type:
        logger.FORGE_logger.error(
            'Missing "type" field in [condenser.%s] section of %s',
            condenser_config_arg,
            toml_file,
        )
        return None
    return condenser_type


def _process_condenser_data(
    condenser_data: dict, condenser_config_arg: str, toml_file: str
) -> dict | None:
    """Process condenser data, handling LLM configs if needed."""
    condenser_type = condenser_data.get("type")
    if (
        condenser_type in ("llm", "llm_attention", "structured")
        and "llm_config" in condenser_data
        and isinstance(condenser_data["llm_config"], str)
    ):
        return _process_llm_condenser(condenser_data, condenser_config_arg, toml_file)
    return condenser_data


def _create_condenser_config(
    condenser_type: str,
    condenser_data: dict,
    condenser_config_arg: str,
    toml_file: str,
) -> "CondenserConfig | None":
    """Create and return CondenserConfig object."""
    try:
        from forge.core.config.condenser_config import create_condenser_config

        config = create_condenser_config(condenser_type, condenser_data)
        logger.FORGE_logger.info(
            "Successfully loaded condenser config [%s] from %s",
            condenser_config_arg,
            toml_file,
        )
        return config
    except (ValidationError, ValueError) as e:
        logger.FORGE_logger.error(
            "Invalid condenser configuration for [%s]: %s.", condenser_config_arg, e
        )
        return None


def get_condenser_config_arg(
    condenser_config_arg: str, toml_file: str = "config.toml"
) -> "CondenserConfig | None":
    """Get a group of condenser settings from the config file by name.

    A group in config.toml can look like this:

    ```
    [condenser.my_summarizer]
    type = 'llm'
    llm_config = 'gpt-4o' # References [llm.gpt-4o]
    max_size = 50
    ...
    ```

    The user-defined group name, like "my_summarizer", is the argument to this function.
    The function will load the CondenserConfig object with the settings of this group,
    from the config file.

    Note that the group must be under the "condenser" group, or in other words,
    the group name must start with "condenser.".

    Args:
        condenser_config_arg: The group of condenser settings to get from the config.toml file.
        toml_file: Path to the configuration file to read from. Defaults to 'config.toml'.

    Returns:
        CondenserConfig: The CondenserConfig object with the settings from the config file, or None if not found/error.

    """
    condenser_config_arg = _normalize_condenser_config_arg(condenser_config_arg)
    logger.FORGE_logger.debug(
        "Loading condenser config [%s] from %s", condenser_config_arg, toml_file
    )

    toml_config = _load_toml_config(toml_file)
    if toml_config is None:
        return None

    condenser_data = _validate_condenser_section(
        toml_config, condenser_config_arg, toml_file
    )
    if condenser_data is None:
        return None

    condenser_type = _validate_condenser_type(
        condenser_data, condenser_config_arg, toml_file
    )
    if condenser_type is None:
        return None

    condenser_data = _process_condenser_data(
        condenser_data, condenser_config_arg, toml_file
    )
    if condenser_data is None:
        return None

    return _create_condenser_config(
        condenser_type, condenser_data, condenser_config_arg, toml_file
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = get_headless_parser()
    args = parser.parse_args()
    if args.version:
        sys.exit(0)
    return args


def register_custom_agents(config: ForgeConfig) -> None:
    """Register custom agents from configuration.

    This function is called after configuration is loaded to ensure all custom agents
    specified in the config are properly imported and registered.
    """
    from forge.controller.agent import Agent

    for agent_name, agent_config in config.agents.items():
        classpath = getattr(agent_config, "classpath", None)
        if classpath:
            try:
                agent_cls = get_impl(Agent, classpath)
                Agent.register(agent_name, agent_cls)
                logger.FORGE_logger.info(
                    "Registered custom agent '%s' from %s", agent_name, classpath
                )
            except Exception as e:
                logger.FORGE_logger.error(
                    "Failed to register agent '%s': %s", agent_name, e
                )


def load_FORGE_config(
    set_logging_levels: bool = True, config_file: str = "config.toml"
) -> ForgeConfig:
    """Load the configuration from the specified config file and environment variables.

    Args:
        set_logging_levels: Whether to set the global variables for logging levels.
        config_file: Path to the config file. Defaults to 'config.toml' in the current directory.

    """
    # Rebuild models to resolve forward references before instantiation
    # Rebuild in dependency order: base configs first, then dependent configs
    from forge.core.config.permissions_config import PermissionsConfig
    from forge.security.safety_config import SafetyConfig

    # Base configs with no dependencies
    LLMConfig.model_rebuild()
    SandboxConfig.model_rebuild()
    SecurityConfig.model_rebuild()
    ExtendedConfig.model_rebuild()
    # KubernetesConfig.model_rebuild()
    MCPConfig.model_rebuild()
    PermissionsConfig.model_rebuild()
    SafetyConfig.model_rebuild()

    # Condenser configs depend on LLMConfig and are Union types
    # We need to provide LLMConfig in the namespace since it's in TYPE_CHECKING block
    from forge.core.config.condenser_config import (
        NoOpCondenserConfig,
        ObservationMaskingCondenserConfig,
        BrowserOutputCondenserConfig,
        RecentEventsCondenserConfig,
        LLMSummarizingCondenserConfig,
        AmortizedForgettingCondenserConfig,
        LLMAttentionCondenserConfig,
        StructuredSummaryCondenserConfig,
        CondenserPipelineConfig,
        ConversationWindowCondenserConfig,
        SmartCondenserConfig,
        CondenserConfig,
    )

    # Create namespace with all necessary imports for condenser configs
    condenser_namespace = {
        "LLMConfig": LLMConfig,
        "Field": Field,
        "BaseModel": BaseModel,
        "ConfigDict": ConfigDict,
        "ValidationError": ValidationError,
        "Literal": Literal,
        "cast": cast,
    }

    # Rebuild individual condenser config classes
    NoOpCondenserConfig.model_rebuild(_types_namespace=condenser_namespace)
    ObservationMaskingCondenserConfig.model_rebuild(
        _types_namespace=condenser_namespace
    )
    BrowserOutputCondenserConfig.model_rebuild(_types_namespace=condenser_namespace)
    RecentEventsCondenserConfig.model_rebuild(_types_namespace=condenser_namespace)
    LLMSummarizingCondenserConfig.model_rebuild(_types_namespace=condenser_namespace)
    AmortizedForgettingCondenserConfig.model_rebuild(
        _types_namespace=condenser_namespace
    )
    LLMAttentionCondenserConfig.model_rebuild(_types_namespace=condenser_namespace)
    StructuredSummaryCondenserConfig.model_rebuild(_types_namespace=condenser_namespace)
    CondenserPipelineConfig.model_rebuild(_types_namespace=condenser_namespace)
    ConversationWindowCondenserConfig.model_rebuild(
        _types_namespace=condenser_namespace
    )
    SmartCondenserConfig.model_rebuild(_types_namespace=condenser_namespace)

    # Note: CondenserConfig is a Union type, so it doesn't have model_rebuild()
    # The individual types have been rebuilt above

    # AgentConfig depends on LLMConfig, so rebuild it after LLMConfig
    AgentConfig.model_rebuild()

    # ForgeConfig depends on everything
    ForgeConfig.model_rebuild()

    original_env = dict(os.environ)

    config = ForgeConfig()
    load_from_toml(config, config_file)
    _restore_environment(original_env)
    env_copy = dict(os.environ)
    env_copy.pop("LLM_API_KEY", None)
    load_from_env(config, env_copy)
    finalize_config(config)
    _export_llm_api_keys(config)
    register_custom_agents(config)
    if set_logging_levels:
        logger.DEBUG = config.debug
        logger.DISABLE_COLOR_PRINTING = config.disable_color
    return config


def _resolve_llm_config_from_cli(
    llm_config_name: str, config: ForgeConfig, config_file: str
) -> LLMConfig:
    """Resolve LLM config from CLI parameter."""
    if llm_config_name in config.llms:
        logger.FORGE_logger.debug(
            "Using LLM config '%s' from loaded configuration", llm_config_name
        )
        return config.llms[llm_config_name]

    llm_config = get_llm_config_arg(llm_config_name, config_file)
    if llm_config is None:
        llm_config = _try_user_config_llm(llm_config_name, config_file)

    if llm_config is None:
        msg = f"Cannot find LLM configuration '{llm_config_name}' in any config file"
        raise ValueError(msg)

    return llm_config


def _try_user_config_llm(llm_config_name: str, config_file: str) -> LLMConfig | None:
    """Try to load LLM config from user config file."""
    user_config = os.path.join(os.path.expanduser("~"), ".Forge", "config.toml")
    if config_file == user_config or not os.path.exists(user_config):
        return None

    logger.FORGE_logger.debug(
        "Trying to load LLM config '%s' from user config: %s",
        llm_config_name,
        user_config,
    )
    return get_llm_config_arg(llm_config_name, user_config)


def _apply_llm_config_override(config: ForgeConfig, args: argparse.Namespace) -> None:
    """Apply LLM config override from CLI arguments."""
    if not args.llm_config:
        return

    logger.FORGE_logger.debug("CLI specified LLM config: %s", args.llm_config)
    llm_config = _resolve_llm_config_from_cli(args.llm_config, config, args.config_file)
    config.set_llm_config(llm_config)
    logger.FORGE_logger.debug("Set LLM config from CLI parameter: %s", args.llm_config)


def _apply_additional_overrides(config: ForgeConfig, args: argparse.Namespace) -> None:
    """Apply additional config overrides from CLI arguments."""
    if hasattr(args, "agent_cls") and args.agent_cls:
        config.default_agent = args.agent_cls
    if hasattr(args, "max_iterations") and args.max_iterations is not None:
        config.max_iterations = args.max_iterations
    if hasattr(args, "max_budget_per_task") and args.max_budget_per_task is not None:
        config.max_budget_per_task = args.max_budget_per_task


def setup_config_from_args(args: argparse.Namespace) -> ForgeConfig:
    """Load config from toml and override with command line arguments.

    Common setup used by both CLI and main.py entry points.

    Configuration precedence (from highest to lowest):
    1. CLI parameters (e.g., -l for LLM config)
    2. config.toml in current directory (or --config-file location if specified)
    3. ~/.Forge/settings.json and ~/.Forge/config.toml
    """
    config = load_FORGE_config(config_file=args.config_file)
    _apply_llm_config_override(config, args)
    _apply_additional_overrides(config, args)
    return config
