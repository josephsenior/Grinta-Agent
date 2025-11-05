from __future__ import annotations

import copy
import logging
import os
import re
import sys
import threading as _threading
import traceback
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from typing import TYPE_CHECKING, Any, Literal, TextIO

import litellm
from pythonjsonlogger.json import JsonFormatter
from termcolor import colored

if TYPE_CHECKING:
    from collections.abc import Mapping, MutableMapping
    from types import TracebackType

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
DEBUG = os.getenv("DEBUG", "False").lower() in ["true", "1", "yes"]
DEBUG_LLM = os.getenv("DEBUG_LLM", "False").lower() in ["true", "1", "yes"]
LOG_JSON = os.getenv("LOG_JSON", "True").lower() in ["true", "1", "yes"]  # Default to JSON for production
LOG_JSON_LEVEL_KEY = os.getenv("LOG_JSON_LEVEL_KEY", "level")
if DEBUG_LLM:
    confirmation = input(
        "\n⚠️ WARNING: You are enabling DEBUG_LLM which may expose sensitive information like API keys.\nThis should NEVER be enabled in production.\nType 'y' to confirm you understand the risks: ",
    )
    if confirmation.lower() == "y":
        litellm.suppress_debug_info = False
        litellm.set_verbose = True
    else:
        litellm.suppress_debug_info = True
        litellm.set_verbose = False
else:
    litellm.suppress_debug_info = True
    litellm.set_verbose = False
if DEBUG:
    LOG_LEVEL = "DEBUG"
LOG_TO_FILE = os.getenv("LOG_TO_FILE", str(LOG_LEVEL == "DEBUG")).lower() in ["true", "1", "yes"]
DISABLE_COLOR_PRINTING = False
LOG_ALL_EVENTS = os.getenv("LOG_ALL_EVENTS", "False").lower() in ["true", "1", "yes"]
DEBUG_RUNTIME = os.getenv("DEBUG_RUNTIME", "False").lower() in ["true", "1", "yes"]
ColorType = Literal[
    "red",
    "green",
    "yellow",
    "blue",
    "magenta",
    "cyan",
    "light_grey",
    "dark_grey",
    "light_red",
    "light_green",
    "light_yellow",
    "light_blue",
    "light_magenta",
    "light_cyan",
    "white",
]
LOG_COLORS: Mapping[str, ColorType] = {
    "ACTION": "green",
    "USER_ACTION": "light_red",
    "OBSERVATION": "yellow",
    "USER_OBSERVATION": "light_green",
    "DETAIL": "cyan",
    "ERROR": "red",
    "PLAN": "light_magenta",
}


class StackInfoFilter(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno >= logging.ERROR:
            exc_info = sys.exc_info()
            if exc_info and exc_info[0] is not None:
                stack = traceback.format_stack()
                stack = stack[:-3]
                stack_str = "".join(stack)
                record.stack_info = stack_str
                record.exc_info = exc_info
        return True


class NoColorFormatter(logging.Formatter):
    """Formatter for non-colored logging in files."""

    def format(self, record: logging.LogRecord) -> str:
        new_record = _fix_record(record)
        new_record.msg = strip_ansi(new_record.msg)
        return super().format(new_record)


class EnhancedJSONFormatter(JsonFormatter):
    """Enhanced JSON formatter with request IDs and structured data.
    
    Adds comprehensive context fields to all log entries for:
    - Request tracing (request_id, conversation_id)
    - Agent tracking (agent_type, action_type)
    - Cost monitoring (model_used, tokens_consumed, cost_usd)
    - Performance tracking (duration_ms)
    - Debugging (location, thread_name, process_id)
    
    Example log output:
        {
            "timestamp": "2025-11-04T10:15:30.123Z",
            "level": "INFO",
            "message": "Agent step completed",
            "request_id": "req_abc123",
            "conversation_id": "conv_456def",
            "agent_type": "CodeActAgent",
            "action_type": "FileEditAction",
            "model_used": "claude-sonnet-4-20250514",
            "tokens_consumed": 1500,
            "cost_usd": 0.015,
            "duration_ms": 850,
            "location": "agent_controller.py:123",
            "function": "step"
        }
    """
    
    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to JSON log output."""
        super().add_fields(log_record, record, message_dict)
        
        # Request tracing
        request_id = getattr(record, 'request_id', None)
        if request_id:
            log_record['request_id'] = request_id
        
        conversation_id = getattr(record, 'conversation_id', None)
        if conversation_id:
            log_record['conversation_id'] = conversation_id
        
        # Add timestamp in ISO format
        from datetime import datetime
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Agent tracking
        agent_type = getattr(record, 'agent_type', None)
        if agent_type:
            log_record['agent_type'] = agent_type
        
        action_type = getattr(record, 'action_type', None)
        if action_type:
            log_record['action_type'] = action_type
        
        # Cost & performance monitoring
        model_used = getattr(record, 'model_used', None)
        if model_used:
            log_record['model_used'] = model_used
        
        tokens_consumed = getattr(record, 'tokens_consumed', None)
        if tokens_consumed is not None:
            log_record['tokens_consumed'] = tokens_consumed
        
        cost_usd = getattr(record, 'cost_usd', None)
        if cost_usd is not None:
            log_record['cost_usd'] = cost_usd
        
        duration_ms = getattr(record, 'duration_ms', None)
        if duration_ms is not None:
            log_record['duration_ms'] = duration_ms
        
        # Thread/process info for debugging
        log_record['thread_name'] = record.threadName
        log_record['process_id'] = record.process
        
        # Source location
        log_record['location'] = f"{record.filename}:{record.lineno}"
        log_record['function'] = record.funcName


def strip_ansi(s: str) -> str:
    """Remove ANSI escape sequences (terminal color/formatting codes) from string.

    Removes ANSI escape sequences from str, as defined by ECMA-048 in
    http://www.ecma-international.org/publications/files/ECMA-ST/Ecma-048.pdf
    # https://github.com/ewen-lbh/python-strip-ansi/blob/master/strip_ansi/__init__.py
    """
    pattern = re.compile("\\x1B\\[\\d+(;\\d+){0,2}m")
    return pattern.sub("", s)


class ColoredFormatter(logging.Formatter):

    def _get_resolved_msg_type(self, record: logging.LogRecord) -> str:
        """Resolve message type with event source prefix if applicable."""
        msg_type = record.__dict__.get("msg_type", "")
        if event_source := record.__dict__.get("event_source", ""):
            new_msg_type = f"{event_source.upper()}_{msg_type}"
            if new_msg_type in LOG_COLORS:
                return new_msg_type
        return msg_type

    def _format_colored_message(self, record: logging.LogRecord, msg_type: str) -> str:
        """Format message with colors."""
        msg_type_color = colored(msg_type, LOG_COLORS[msg_type])
        msg = colored(record.msg, LOG_COLORS[msg_type])
        time_str = colored(self.formatTime(record, self.datefmt), LOG_COLORS[msg_type])
        name_str = colored(record.name, LOG_COLORS[msg_type])
        level_str = colored(record.levelname, LOG_COLORS[msg_type])

        if msg_type in {"ERROR"} or DEBUG:
            return f"{time_str} - {name_str}:{level_str}: {record.filename}:{record.lineno}\n{msg_type_color}\n{msg}"
        return f"{time_str} - {msg_type_color}\n{msg}"

    def _format_step_message(self, record: logging.LogRecord) -> str:
        """Format STEP message."""
        return f"\n\n==============\n{record.msg}\n" if LOG_ALL_EVENTS else record.msg

    def format(self, record: logging.LogRecord) -> str:
        msg_type = self._get_resolved_msg_type(record)

        if msg_type in LOG_COLORS and (not DISABLE_COLOR_PRINTING):
            return self._format_colored_message(record, msg_type)

        if msg_type == "STEP":
            return self._format_step_message(record)

        new_record = _fix_record(record)
        return super().format(new_record)


def _fix_record(record: logging.LogRecord) -> logging.LogRecord:
    new_record = copy.copy(record)
    if getattr(new_record, "exc_info", None) is True:
        new_record.exc_info = sys.exc_info()
        new_record.stack_info = None
    return new_record


file_formatter = NoColorFormatter(
    "%(asctime)s - %(name)s:%(levelname)s: %(filename)s:%(lineno)s - %(message)s",
    datefmt="%H:%M:%S",
)
llm_formatter = logging.Formatter("%(message)s")


class RollingLogger:
    max_lines: int
    char_limit: int
    log_lines: list[str]
    all_lines: str

    def __init__(self, max_lines: int = 10, char_limit: int = 80) -> None:
        self.max_lines = max_lines
        self.char_limit = char_limit
        self.log_lines = [""] * self.max_lines
        self.all_lines = ""

    def is_enabled(self) -> bool:
        return DEBUG and sys.stdout.isatty()

    def start(self, message: str = "") -> None:
        if message:
            pass
        self._write("\n" * self.max_lines)
        self._flush()

    def add_line(self, line: str) -> None:
        self.log_lines.pop(0)
        self.log_lines.append(line[: self.char_limit])
        self.print_lines()
        self.all_lines += line + "\n"

    def write_immediately(self, line: str) -> None:
        self._write(line)
        self._flush()

    def print_lines(self) -> None:
        """Display the last n log_lines in the console (not for file logging).

        This will create the effect of a rolling display in the console.
        """
        self.move_back()
        for line in self.log_lines:
            self.replace_current_line(line)

    def move_back(self, amount: int = -1) -> None:
        r"""'\\033[F' moves the cursor up one line."""
        if amount == -1:
            amount = self.max_lines
        self._write("\x1b[F" * self.max_lines)
        self._flush()

    def replace_current_line(self, line: str = "") -> None:
        r"""'\\033[2K\\r' clears the line and moves the cursor to the beginning of the line."""
        self._write("\x1b[2K" + line + "\n")
        self._flush()

    def _write(self, line: str) -> None:
        if not self.is_enabled():
            return
        sys.stdout.write(line)

    def _flush(self) -> None:
        if not self.is_enabled():
            return
        sys.stdout.flush()


class SensitiveDataFilter(logging.Filter):

    def filter(self, record: logging.LogRecord) -> bool:
        sensitive_values = []
        for key, value in os.environ.items():
            key_upper = key.upper()
            if (
                len(value) > 2
                and value != "default"
                and any(s in key_upper for s in ("SECRET", "_KEY", "_CODE", "_TOKEN"))
            ):
                sensitive_values.append(value)
        msg = record.getMessage()
        for sensitive_value in sensitive_values:
            msg = msg.replace(sensitive_value, "******")
        sensitive_patterns = [
            "api_key",
            "aws_access_key_id",
            "aws_secret_access_key",
            "e2b_api_key",
            "github_token",
            "jwt_secret",
            "modal_api_token_id",
            "modal_api_token_secret",
            "llm_api_key",
            "sandbox_env_github_token",
            "runloop_api_key",
            "daytona_api_key",
        ]
        env_vars = [attr.upper() for attr in sensitive_patterns]
        sensitive_patterns.extend(env_vars)
        for attr in sensitive_patterns:
            pattern = f"{attr}='?([\\w-]+)'?"
            msg = re.sub(pattern, f"{attr}='******'", msg)
        record.msg = msg
        record.args = ()
        return True


class TraceContextFilter(logging.Filter):
    """Injects any keys from the thread-local trace context into log records.

    Uses threading.local() so concurrent orchestrations running in different
    threads won't clobber each other's trace context.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            ctx = getattr(_TRACE_LOCAL, "context", None) or {}
            for k, v in ctx.items():
                if not hasattr(record, k):
                    setattr(record, k, v)
        except Exception:
            pass
        return True


_TRACE_LOCAL: _threading.local = _threading.local()


def set_trace_context(ctx: dict[str, object] | None) -> None:
    """Set thread-local trace context (overwrites existing). Pass None to clear."""
    try:
        if ctx is None:
            if hasattr(_TRACE_LOCAL, "context"):
                delattr(_TRACE_LOCAL, "context")
        else:
            _TRACE_LOCAL.context = dict(ctx)
    except Exception:
        pass


def clear_trace_context() -> None:
    """Clear the thread-local trace context.
    
    Removes trace context from thread-local storage if it exists.
    Silently handles any exceptions during cleanup.
    """
    try:
        if hasattr(_TRACE_LOCAL, "context"):
            delattr(_TRACE_LOCAL, "context")
    except Exception:
        pass


def get_console_handler(log_level: int = logging.INFO) -> logging.StreamHandler:
    """Returns a console handler for logging."""
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    formatter_str = "\x1b[92m%(asctime)s - %(name)s:%(levelname)s\x1b[0m: %(filename)s:%(lineno)s - %(message)s"
    console_handler.setFormatter(ColoredFormatter(formatter_str, datefmt="%H:%M:%S"))
    return console_handler


def get_file_handler(
    log_dir: str,
    log_level: int = logging.INFO,
    when: str = "d",
    backup_count: int = 7,
    utc: bool = False,
) -> TimedRotatingFileHandler:
    """Returns a file handler for logging."""
    os.makedirs(log_dir, exist_ok=True)
    file_name = "openhands.log"
    file_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, file_name),
        when=when,
        backupCount=backup_count,
        utc=utc,
    )
    file_handler.setLevel(log_level)
    if LOG_JSON:
        file_handler.setFormatter(json_formatter())
    else:
        file_handler.setFormatter(file_formatter)
    return file_handler


def json_formatter() -> JsonFormatter:
    """Create JSON formatter for structured logging.
    
    Returns:
        JsonFormatter configured with timestamp and custom level field naming
    """
    fmt = "{asctime} {message} {levelname}"
    return JsonFormatter(fmt, style="{", rename_fields={"levelname": LOG_JSON_LEVEL_KEY}, timestamp=True)


def json_log_handler(level: int = logging.INFO, _out: TextIO = sys.stdout) -> logging.Handler:
    """Configure logger instance for structured logging as json lines."""
    handler = logging.StreamHandler(_out)
    handler.setLevel(level)
    handler.setFormatter(json_formatter())
    return handler


logging.basicConfig(level=logging.ERROR)


def log_uncaught_exceptions(ex_cls: type[BaseException], ex: BaseException, tb: TracebackType | None) -> Any:
    """Logs uncaught exceptions along with the traceback.

    Args:
        ex_cls: The type of the exception.
        ex: The exception instance.
        tb: The traceback object.

    Returns:
        None
    """
    if tb:
        logging.error("".join(traceback.format_tb(tb)))
    logging.error(f"{ex_cls}: {ex}")


sys.excepthook = log_uncaught_exceptions
openhands_logger = logging.getLogger("openhands")
current_log_level = logging.INFO
if LOG_LEVEL in logging.getLevelNamesMapping():
    current_log_level = logging.getLevelNamesMapping()[LOG_LEVEL]
openhands_logger.setLevel(current_log_level)
if DEBUG:
    openhands_logger.addFilter(StackInfoFilter())
if current_log_level == logging.DEBUG:
    openhands_logger.debug("DEBUG mode enabled.")
if LOG_JSON:
    openhands_logger.addHandler(json_log_handler(current_log_level))
else:
    openhands_logger.addHandler(get_console_handler(current_log_level))
openhands_logger.addFilter(SensitiveDataFilter(openhands_logger.name))
openhands_logger.addFilter(TraceContextFilter())
openhands_logger.propagate = False
openhands_logger.debug("Logging initialized")
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
if LOG_TO_FILE:
    openhands_logger.addHandler(get_file_handler(LOG_DIR, current_log_level))
    openhands_logger.debug(f"Logging to file in: {LOG_DIR}")
logging.getLogger("LiteLLM").disabled = True
logging.getLogger("LiteLLM Router").disabled = True
logging.getLogger("LiteLLM Proxy").disabled = True
LOQUACIOUS_LOGGERS = ["engineio", "engineio.server", "socketio", "socketio.client", "socketio.server"]
for logger_name in LOQUACIOUS_LOGGERS:
    logging.getLogger(logger_name).setLevel("WARNING")


class LlmFileHandler(logging.FileHandler):
    """LLM prompt and response logging."""

    def __init__(self, filename: str, mode: str = "a", encoding: str = "utf-8", delay: bool = False) -> None:
        """Initializes an instance of LlmFileHandler.

        Args:
            filename (str): The name of the log file.
            mode (str, optional): The file mode. Defaults to 'a'.
            encoding (str, optional): The file encoding. Defaults to None.
            delay (bool, optional): Whether to delay file opening. Defaults to False.
        """
        self.filename = filename
        self.message_counter = 1
        if DEBUG:
            self.session = datetime.now().strftime("%y-%m-%d_%H-%M")
        else:
            self.session = "default"
        self.log_directory = os.path.join(LOG_DIR, "llm", self.session)
        os.makedirs(self.log_directory, exist_ok=True)
        if not DEBUG:
            for file in os.listdir(self.log_directory):
                file_path = os.path.join(self.log_directory, file)
                try:
                    os.unlink(file_path)
                except Exception as e:
                    openhands_logger.exception("Failed to delete %s. Reason: %s", file_path, e)
        filename = f"{self.filename}_{self.message_counter:03}.log"
        self.baseFilename = os.path.join(self.log_directory, filename)
        super().__init__(self.baseFilename, mode, encoding, delay)

    def emit(self, record: logging.LogRecord) -> None:
        """Emits a log record.

        Args:
            record (logging.LogRecord): The log record to emit.
        """
        filename = f"{self.filename}_{self.message_counter:03}.log"
        self.baseFilename = os.path.join(self.log_directory, filename)
        self.stream = self._open()
        super().emit(record)
        self.stream.close()
        openhands_logger.debug("Logging to %s", self.baseFilename)
        self.message_counter += 1


def _get_llm_file_handler(name: str, log_level: int) -> LlmFileHandler:
    llm_file_handler = LlmFileHandler(name, delay=True)
    llm_file_handler.setFormatter(llm_formatter)
    llm_file_handler.setLevel(log_level)
    return llm_file_handler


def _setup_llm_logger(name: str, log_level: int) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.propagate = False
    logger.setLevel(log_level)
    if LOG_TO_FILE:
        logger.addHandler(_get_llm_file_handler(name, log_level))
    return logger


llm_prompt_logger = _setup_llm_logger("prompt", current_log_level)
llm_response_logger = _setup_llm_logger("response", current_log_level)


class OpenHandsLoggerAdapter(logging.LoggerAdapter):
    extra: dict

    def __init__(self, logger: logging.Logger = openhands_logger, extra: dict | None = None) -> None:
        self.logger = logger
        self.extra = extra or {}

    def bind(self, **context: Any) -> OpenHandsLoggerAdapter:
        """Return a new adapter with additional context merged into extra.

        Example: adapter.bind(trace_id='abc', goal_id='g1')
        """
        new_extra = {**self.extra, **context}
        return OpenHandsLoggerAdapter(self.logger, new_extra)

    def process(self, msg: str, kwargs: MutableMapping[str, Any]) -> tuple[str, MutableMapping[str, Any]]:
        """If 'extra' is supplied in kwargs, merge it with the adapters 'extra' dict.

        Starting in Python 3.13, LoggerAdapter's merge_extra option will do this.
        """
        if "extra" in kwargs and isinstance(kwargs["extra"], dict):
            kwargs["extra"] = {**self.extra, **kwargs["extra"]}
        else:
            kwargs["extra"] = self.extra
        return (msg, kwargs)


def bind_context(logger: logging.Logger | OpenHandsLoggerAdapter, **context: Any) -> OpenHandsLoggerAdapter:
    """Utility to bind tracing/context information to a logger.

    Returns an OpenHandsLoggerAdapter which will include the provided context in all
    emitted logs via the `extra` dict. Intended keys: trace_id, goal_id, step_id, event_source, msg_type.
    """
    if isinstance(logger, OpenHandsLoggerAdapter):
        return logger.bind(**context)
    return OpenHandsLoggerAdapter(logger, context)
